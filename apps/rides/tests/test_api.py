import pytest

from apps.drivers.domain import Availability
from conftest import _client_for

pytestmark = pytest.mark.django_db

URL = "/api/v1/rides/"


def test_anonymous_cannot_request_ride(anon_client, ride_payload):
    assert anon_client.post(URL, ride_payload, format="json").status_code == 401


def test_request_ride_returns_assigned_driver(rider_client, ride_payload, place_driver):
    driver = place_driver()

    response = rider_client.post(URL, ride_payload, format="json")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "assigned"
    assert body["driver"]["id"] == driver.id
    assert body["driver"]["phone"] == driver.phone
    assert body["estimated_fare"] > 0


def test_no_driver_available_returns_503(rider_client, ride_payload):
    response = rider_client.post(URL, ride_payload, format="json")

    assert response.status_code == 503
    assert "detail" in response.json()


def test_second_active_ride_returns_409(rider_client, ride_payload, place_driver):
    place_driver(0.2)
    place_driver(0.4)
    rider_client.post(URL, ride_payload, format="json")

    response = rider_client.post(URL, ride_payload, format="json")

    assert response.status_code == 409


def test_pickup_equal_to_dropoff_returns_400(rider_client, ride_payload):
    ride_payload["dropoff_latitude"] = ride_payload["pickup_latitude"]
    ride_payload["dropoff_longitude"] = ride_payload["pickup_longitude"]

    response = rider_client.post(URL, ride_payload, format="json")

    assert response.status_code == 400


def test_invalid_coordinates_return_400(rider_client, ride_payload):
    ride_payload["pickup_latitude"] = 100

    response = rider_client.post(URL, ride_payload, format="json")

    assert response.status_code == 400
    assert "pickup_latitude" in response.json()


def test_rider_and_driver_can_view_ride_but_strangers_cannot(
    rider_client, other_client, ride_payload, place_driver
):
    driver = place_driver()
    ride_id = rider_client.post(URL, ride_payload, format="json").json()["id"]
    driver_client = _client_for(driver.user)

    assert rider_client.get(f"{URL}{ride_id}/").status_code == 200
    assert driver_client.get(f"{URL}{ride_id}/").status_code == 200
    assert other_client.get(f"{URL}{ride_id}/").status_code == 404


def test_current_ride_for_rider_and_driver(rider_client, ride_payload, place_driver):
    driver = place_driver()
    ride_id = rider_client.post(URL, ride_payload, format="json").json()["id"]

    assert rider_client.get(f"{URL}current/").json()["id"] == ride_id
    assert _client_for(driver.user).get(f"{URL}current/").json()["id"] == ride_id


def test_no_current_ride_returns_404(rider_client):
    assert rider_client.get(f"{URL}current/").status_code == 404


def test_full_trip_flow(rider_client, ride_payload, place_driver):
    driver = place_driver()
    driver_client = _client_for(driver.user)
    ride_id = rider_client.post(URL, ride_payload, format="json").json()["id"]

    assert (
        driver_client.post(f"{URL}{ride_id}/start/").json()["status"] == "in_progress"
    )
    completed = driver_client.post(f"{URL}{ride_id}/complete/").json()

    assert completed["status"] == "completed"
    assert completed["completed_at"] is not None
    driver.refresh_from_db()
    assert driver.availability == Availability.AVAILABLE


def test_rider_cannot_start_ride(rider_client, ride_payload, place_driver):
    place_driver()
    ride_id = rider_client.post(URL, ride_payload, format="json").json()["id"]

    assert rider_client.post(f"{URL}{ride_id}/start/").status_code == 404


def test_complete_before_start_returns_409(rider_client, ride_payload, place_driver):
    driver = place_driver()
    ride_id = rider_client.post(URL, ride_payload, format="json").json()["id"]

    response = _client_for(driver.user).post(f"{URL}{ride_id}/complete/")

    assert response.status_code == 409


def test_rider_cancels_ride(rider_client, ride_payload, place_driver):
    driver = place_driver()
    ride_id = rider_client.post(URL, ride_payload, format="json").json()["id"]

    response = rider_client.post(f"{URL}{ride_id}/cancel/")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    driver.refresh_from_db()
    assert driver.can_accept_ride()


def test_driver_cannot_go_offline_during_assigned_ride(
    rider_client, ride_payload, place_driver
):
    driver = place_driver()
    rider_client.post(URL, ride_payload, format="json")

    response = _client_for(driver.user).post("/api/v1/drivers/me/offline/")

    assert response.status_code == 409
