import pytest
from django.utils import timezone

from apps.drivers.domain import Availability
from apps.rides.models import RideOffer
from apps.rides.tests.conftest import book
from conftest import _client_for

pytestmark = pytest.mark.django_db

URL = "/api/v1/rides/"
OFFERS_URL = f"{URL}offers/"


def test_anonymous_cannot_request_ride(anon_client, ride_payload):
    assert anon_client.post(URL, ride_payload, format="json").status_code == 401


def test_request_ride_starts_searching(rider_client, ride_payload, place_driver):
    place_driver()

    response = rider_client.post(URL, ride_payload, format="json")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "searching"
    assert body["driver"] is None
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


def test_driver_sees_offer_and_accepts(rider_client, ride_payload, place_driver):
    driver = place_driver()
    driver_client = _client_for(driver.user)
    ride_id = rider_client.post(URL, ride_payload, format="json").json()["id"]

    offer = driver_client.get(f"{OFFERS_URL}current/").json()
    assert offer["ride"]["id"] == ride_id

    response = driver_client.post(f"{OFFERS_URL}{offer['id']}/accept/")

    assert response.status_code == 200
    assert response.json()["status"] == "assigned"
    assert response.json()["driver"]["id"] == driver.id
    assert rider_client.get(f"{URL}current/").json()["status"] == "assigned"


def test_driver_declines_offer(rider_client, ride_payload, place_driver):
    driver = place_driver()
    driver_client = _client_for(driver.user)
    ride_id = rider_client.post(URL, ride_payload, format="json").json()["id"]
    offer_id = driver_client.get(f"{OFFERS_URL}current/").json()["id"]

    response = driver_client.post(f"{OFFERS_URL}{offer_id}/decline/")

    assert response.status_code == 204
    assert rider_client.get(f"{URL}{ride_id}/").json()["status"] == "no_driver"
    assert rider_client.get(f"{URL}current/").status_code == 404


def test_no_current_offer_returns_404(user_client):
    assert user_client.get(f"{OFFERS_URL}current/").status_code == 404


def test_accept_someone_elses_offer_returns_404(
    rider_client, other_client, ride_payload, place_driver
):
    place_driver()
    rider_client.post(URL, ride_payload, format="json")
    offer = RideOffer.objects.get()

    assert other_client.post(f"{OFFERS_URL}{offer.id}/accept/").status_code == 404


def test_accept_expired_offer_returns_409(rider_client, ride_payload, place_driver):
    driver = place_driver()
    rider_client.post(URL, ride_payload, format="json")
    offer = RideOffer.objects.get()
    RideOffer.objects.filter(pk=offer.pk).update(expires_at=timezone.now())

    response = _client_for(driver.user).post(f"{OFFERS_URL}{offer.id}/accept/")

    assert response.status_code == 409


def test_rider_polling_moves_expired_offer_on(rider_client, ride_payload, place_driver):
    first = place_driver(0.2)
    second = place_driver(1.0)
    rider_client.post(URL, ride_payload, format="json")
    RideOffer.objects.filter(driver=first).update(expires_at=timezone.now())

    assert rider_client.get(f"{URL}current/").json()["status"] == "searching"
    assert RideOffer.objects.get(status="pending").driver_id == second.id


def test_rider_and_driver_can_view_ride_but_strangers_cannot(
    rider, rider_client, other_client, place_driver
):
    driver = place_driver()
    ride = book(rider)

    assert rider_client.get(f"{URL}{ride.id}/").status_code == 200
    assert _client_for(driver.user).get(f"{URL}{ride.id}/").status_code == 200
    assert other_client.get(f"{URL}{ride.id}/").status_code == 404


def test_offered_driver_does_not_see_ride_before_accepting(
    rider, rider_client, ride_payload, place_driver
):
    driver = place_driver()
    ride_id = rider_client.post(URL, ride_payload, format="json").json()["id"]

    assert _client_for(driver.user).get(f"{URL}{ride_id}/").status_code == 404


def test_current_ride_for_rider_and_driver(rider, rider_client, place_driver):
    driver = place_driver()
    ride = book(rider)

    assert rider_client.get(f"{URL}current/").json()["id"] == ride.id
    assert _client_for(driver.user).get(f"{URL}current/").json()["id"] == ride.id


def test_no_current_ride_returns_404(rider_client):
    assert rider_client.get(f"{URL}current/").status_code == 404


def test_full_trip_flow(rider, place_driver):
    driver = place_driver()
    driver_client = _client_for(driver.user)
    ride = book(rider)

    assert (
        driver_client.post(f"{URL}{ride.id}/start/").json()["status"] == "in_progress"
    )
    completed = driver_client.post(f"{URL}{ride.id}/complete/").json()

    assert completed["status"] == "completed"
    assert completed["completed_at"] is not None
    driver.refresh_from_db()
    assert driver.availability == Availability.AVAILABLE


def test_rider_cannot_start_ride(rider, rider_client, place_driver):
    place_driver()
    ride = book(rider)

    assert rider_client.post(f"{URL}{ride.id}/start/").status_code == 404


def test_complete_before_start_returns_409(rider, place_driver):
    driver = place_driver()
    ride = book(rider)

    response = _client_for(driver.user).post(f"{URL}{ride.id}/complete/")

    assert response.status_code == 409


def test_rider_cancels_searching_ride(rider_client, ride_payload, place_driver):
    driver = place_driver()
    ride_id = rider_client.post(URL, ride_payload, format="json").json()["id"]

    response = rider_client.post(f"{URL}{ride_id}/cancel/")

    assert response.json()["status"] == "cancelled"
    assert _client_for(driver.user).get(f"{OFFERS_URL}current/").status_code == 404


def test_rider_cancels_assigned_ride(rider, rider_client, place_driver):
    driver = place_driver()
    ride = book(rider)

    response = rider_client.post(f"{URL}{ride.id}/cancel/")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    driver.refresh_from_db()
    assert driver.can_accept_ride()


def test_driver_cannot_go_offline_during_assigned_ride(rider, place_driver):
    driver = place_driver()
    book(rider)

    response = _client_for(driver.user).post("/api/v1/drivers/me/offline/")

    assert response.status_code == 409


def test_offer_shows_trip_details_to_driver(rider_client, ride_payload, place_driver):
    driver = place_driver()
    rider_client.post(URL, ride_payload, format="json")

    offer = _client_for(driver.user).get(f"{OFFERS_URL}current/").json()

    assert offer["ride"]["pickup_latitude"] == ride_payload["pickup_latitude"]
    assert offer["ride"]["estimated_fare"] > 0
    assert offer["expires_at"]
