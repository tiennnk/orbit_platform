import pytest

from apps.drivers.models import DriverLocation
from apps.rides.pricing import estimate_eta_minutes
from apps.rides.services import cancel_ride, complete_ride, start_ride
from apps.rides.tests.conftest import KM_IN_LAT_DEGREES, PICKUP, book, request

pytestmark = pytest.mark.django_db


def url(ride_id):
    return f"/api/v1/rides/{ride_id}/driver-position/"


def test_rider_sees_driver_heading_to_pickup(rider, rider_client, place_driver):
    place_driver(2.0)
    ride = book(rider)

    body = rider_client.get(url(ride.id)).json()

    assert body["heading_to"] == "pickup"
    assert body["latitude"] == pytest.approx(PICKUP[0] + 2.0 * KM_IN_LAT_DEGREES)
    assert body["distance_km"] == pytest.approx(2.6, abs=0.01)
    assert body["eta_minutes"] == 7


def test_position_follows_latest_location(rider, rider_client, place_driver):
    driver = place_driver(2.0)
    ride = book(rider)
    DriverLocation.objects.filter(driver=driver).update(latitude=PICKUP[0])

    body = rider_client.get(url(ride.id)).json()

    assert body["latitude"] == PICKUP[0]
    assert body["distance_km"] == 0
    assert body["eta_minutes"] == 1


def test_heading_to_dropoff_once_started(rider, rider_client, place_driver):
    driver = place_driver()
    ride = book(rider)
    start_ride(ride_id=ride.id, user=driver.user)

    assert rider_client.get(url(ride.id)).json()["heading_to"] == "dropoff"


def test_searching_ride_has_no_position(rider, rider_client, place_driver):
    place_driver()
    ride = request(rider)

    assert rider_client.get(url(ride.id)).status_code == 404


@pytest.mark.parametrize("finish", ["complete", "cancel"])
def test_finished_ride_hides_position(rider, rider_client, place_driver, finish):
    driver = place_driver()
    ride = book(rider)
    if finish == "complete":
        start_ride(ride_id=ride.id, user=driver.user)
        complete_ride(ride_id=ride.id, user=driver.user)
    else:
        cancel_ride(ride_id=ride.id, user=rider)

    assert rider_client.get(url(ride.id)).status_code == 404


def test_driver_without_location_returns_404(rider, rider_client, place_driver):
    driver = place_driver()
    ride = book(rider)
    DriverLocation.objects.filter(driver=driver).delete()

    response = rider_client.get(url(ride.id))

    assert response.status_code == 404
    assert "location" in response.json()["detail"]


def test_only_the_rider_can_track(rider, other_client, place_driver):
    place_driver()
    ride = book(rider)

    assert other_client.get(url(ride.id)).status_code == 404


@pytest.mark.parametrize(
    ("distance_km", "minutes"),
    [(0, 1), (0.1, 1), (2.6, 7), (25, 60)],
)
def test_eta_minutes(distance_km, minutes):
    assert estimate_eta_minutes(distance_km=distance_km) == minutes
