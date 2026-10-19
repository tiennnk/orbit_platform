from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.drivers.domain import DriverNotOnline
from apps.drivers.models import DriverLocation
from apps.drivers.services import update_location

pytestmark = pytest.mark.django_db

LOCATION_URL = "/api/v1/drivers/me/location/"

LAT, LNG = 10.7725, 106.6980


def test_offline_driver_cannot_update_location(driver):
    with pytest.raises(DriverNotOnline):
        update_location(
            driver=driver, latitude=LAT, longitude=LNG, recorded_at=timezone.now()
        )

    assert not DriverLocation.objects.exists()


def test_first_update_creates_location(online_driver):
    now = timezone.now()

    location = update_location(
        driver=online_driver, latitude=LAT, longitude=LNG, recorded_at=now
    )

    location.refresh_from_db()
    assert (location.latitude, location.longitude) == (LAT, LNG)
    assert location.recorded_at == now


def test_newer_update_overwrites_location(online_driver):
    t0 = timezone.now()
    update_location(driver=online_driver, latitude=LAT, longitude=LNG, recorded_at=t0)

    update_location(
        driver=online_driver,
        latitude=10.8,
        longitude=106.7,
        recorded_at=t0 + timedelta(seconds=5),
    )

    location = DriverLocation.objects.get(driver=online_driver)
    assert (location.latitude, location.longitude) == (10.8, 106.7)
    assert DriverLocation.objects.count() == 1


def test_out_of_order_older_update_is_ignored(online_driver):
    t0 = timezone.now()
    update_location(
        driver=online_driver, latitude=10.8, longitude=106.7, recorded_at=t0
    )

    update_location(
        driver=online_driver,
        latitude=LAT,
        longitude=LNG,
        recorded_at=t0 - timedelta(seconds=5),
    )

    location = DriverLocation.objects.get(driver=online_driver)
    assert (location.latitude, location.longitude) == (10.8, 106.7)
    assert location.recorded_at == t0


def test_database_rejects_invalid_latitude(online_driver):
    with pytest.raises(IntegrityError):
        DriverLocation.objects.create(
            driver=online_driver, latitude=91, longitude=LNG, recorded_at=timezone.now()
        )


def _payload(**overrides):
    payload = {
        "latitude": LAT,
        "longitude": LNG,
        "recorded_at": timezone.now().isoformat(),
    }
    payload.update(overrides)
    return payload


def test_online_driver_updates_location_via_api(online_driver, user_client):
    response = user_client.put(LOCATION_URL, _payload(), format="json")

    assert response.status_code == 200
    body = response.json()
    assert (body["latitude"], body["longitude"]) == (LAT, LNG)
    assert DriverLocation.objects.get(driver=online_driver).latitude == LAT


def test_offline_driver_gets_409(driver, user_client):
    response = user_client.put(LOCATION_URL, _payload(), format="json")

    assert response.status_code == 409


@pytest.mark.parametrize(
    "field, value",
    [
        ("latitude", 90.0001),
        ("latitude", -91),
        ("longitude", 180.5),
        ("longitude", -181),
    ],
)
def test_out_of_range_coordinates_return_400(online_driver, user_client, field, value):
    response = user_client.put(LOCATION_URL, _payload(**{field: value}), format="json")

    assert response.status_code == 400
    assert field in response.json()


def test_recorded_at_in_the_future_returns_400(online_driver, user_client):
    future = (timezone.now() + timedelta(minutes=5)).isoformat()

    response = user_client.put(
        LOCATION_URL, _payload(recorded_at=future), format="json"
    )

    assert response.status_code == 400
    assert "recorded_at" in response.json()


def test_update_location_without_profile_returns_404(user_client):
    response = user_client.put(LOCATION_URL, _payload(), format="json")

    assert response.status_code == 404


def test_anonymous_cannot_update_location(anon_client):
    response = anon_client.put(LOCATION_URL, _payload(), format="json")

    assert response.status_code == 401
