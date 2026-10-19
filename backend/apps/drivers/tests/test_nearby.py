from datetime import timedelta
from itertools import count

import pytest
from django.utils import timezone

from apps.drivers.domain import ApprovalStatus, Availability
from apps.drivers.models import Driver, DriverLocation
from apps.drivers.selectors import find_nearby_drivers

pytestmark = pytest.mark.django_db

NEARBY_URL = "/api/v1/drivers/nearby/"
ORIGIN = (10.7769, 106.7009)
KM_IN_LAT_DEGREES = 1 / 111.19

_sequence = count()


@pytest.fixture
def place_driver(django_user_model):
    def _place(
        km_north: float,
        *,
        approval_status=ApprovalStatus.APPROVED,
        is_online=True,
        availability=Availability.AVAILABLE,
        age=timedelta(seconds=0),
    ) -> Driver:
        n = next(_sequence)
        user = django_user_model.objects.create_user(username=f"nearby{n}")
        driver = Driver.objects.create(
            user=user,
            full_name=f"Driver {n}",
            phone=f"08{n:08d}",
            approval_status=approval_status,
            is_online=is_online,
            availability=availability,
        )
        DriverLocation.objects.create(
            driver=driver,
            latitude=ORIGIN[0] + km_north * KM_IN_LAT_DEGREES,
            longitude=ORIGIN[1],
            recorded_at=timezone.now(),
        )
        DriverLocation.objects.filter(driver=driver).update(
            updated_at=timezone.now() - age
        )
        return driver

    return _place


def find(**kwargs):
    return find_nearby_drivers(latitude=ORIGIN[0], longitude=ORIGIN[1], **kwargs)


def test_returns_drivers_sorted_by_distance(place_driver):
    far = place_driver(2.0)
    near = place_driver(0.5)
    middle = place_driver(1.0)

    result = find(radius_km=3)

    assert [n.driver.id for n in result] == [near.id, middle.id, far.id]
    assert result[0].distance_km == pytest.approx(0.5, abs=0.01)


def test_excludes_drivers_outside_radius(place_driver):
    inside = place_driver(2.9)
    place_driver(3.1)

    assert [n.driver.id for n in find(radius_km=3)] == [inside.id]


def test_box_corner_is_outside_the_circle(place_driver):
    driver = place_driver(0)
    DriverLocation.objects.filter(driver=driver).update(
        latitude=ORIGIN[0] + 2.9 * KM_IN_LAT_DEGREES,
        longitude=ORIGIN[1] + 2.9 * KM_IN_LAT_DEGREES,
    )

    assert find(radius_km=3) == []


def test_respects_limit(place_driver):
    drivers = [place_driver(0.1 * i) for i in range(1, 6)]

    result = find(radius_km=3, limit=2)

    assert [n.driver.id for n in result] == [drivers[0].id, drivers[1].id]


@pytest.mark.parametrize(
    "state",
    [
        {"is_online": False},
        {"approval_status": ApprovalStatus.PENDING, "is_online": False},
        {"availability": Availability.ON_TRIP},
        {"age": timedelta(minutes=5)},
    ],
    ids=["offline", "not-approved", "on-trip", "stale-location"],
)
def test_excludes_ineligible_drivers(place_driver, state):
    place_driver(0.5, **state)

    assert find(radius_km=3) == []


def test_can_exclude_specific_drivers(place_driver):
    first = place_driver(0.5)
    second = place_driver(1.0)

    result = find(radius_km=3, exclude_driver_ids=frozenset({first.id}))

    assert [n.driver.id for n in result] == [second.id]


def test_nearby_endpoint_for_staff(place_driver, staff_client):
    driver = place_driver(1.0)

    response = staff_client.get(
        NEARBY_URL, {"latitude": ORIGIN[0], "longitude": ORIGIN[1], "radius_km": 3}
    )

    assert response.status_code == 200
    [item] = response.json()
    assert item["driver_id"] == driver.id
    assert item["distance_km"] == pytest.approx(1.0, abs=0.01)


def test_nearby_endpoint_validates_query(staff_client):
    response = staff_client.get(NEARBY_URL, {"latitude": 95, "longitude": 0})

    assert response.status_code == 400
    assert "latitude" in response.json()


def test_nearby_endpoint_is_staff_only(user_client):
    response = user_client.get(
        NEARBY_URL, {"latitude": ORIGIN[0], "longitude": ORIGIN[1]}
    )

    assert response.status_code == 403
