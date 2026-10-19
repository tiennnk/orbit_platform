import pytest

from apps.rides.services import cancel_ride, complete_ride, start_ride
from apps.rides.tests.conftest import book
from conftest import _client_for

pytestmark = pytest.mark.django_db

URL = "/api/v1/rides/history/"


def finished_ride(rider, driver):
    ride = book(rider)
    start_ride(ride_id=ride.id, user=driver.user)
    return complete_ride(ride_id=ride.id, user=driver.user)


def test_rider_sees_own_rides_newest_first(rider, rider_client, place_driver):
    driver = place_driver()
    first = finished_ride(rider, driver)
    second = cancel_ride(ride_id=book(rider).id, user=rider)
    third = book(rider)

    response = rider_client.get(URL)

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert [r["id"] for r in body["results"]] == [third.id, second.id, first.id]
    assert [r["status"] for r in body["results"]] == [
        "assigned",
        "cancelled",
        "completed",
    ]


def test_driver_role_shows_rides_driven(rider, place_driver):
    driver = place_driver()
    ride = finished_ride(rider, driver)

    response = _client_for(driver.user).get(URL, {"role": "driver"})

    assert [r["id"] for r in response.json()["results"]] == [ride.id]


def test_driver_role_without_profile_is_empty(rider_client):
    response = rider_client.get(URL, {"role": "driver"})

    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_rider_role_does_not_include_rides_driven(rider, place_driver):
    driver = place_driver()
    finished_ride(rider, driver)

    response = _client_for(driver.user).get(URL)

    assert response.json()["count"] == 0


def test_other_users_rides_are_not_visible(rider, other_client, place_driver):
    finished_ride(rider, place_driver())

    assert other_client.get(URL).json()["count"] == 0


def test_invalid_role_returns_400(rider_client):
    response = rider_client.get(URL, {"role": "admin"})

    assert response.status_code == 400
    assert "role" in response.json()


def test_history_is_paginated(rider, rider_client, place_driver):
    driver = place_driver()
    for _ in range(3):
        finished_ride(rider, driver)

    body = rider_client.get(URL, {"page_size": 2}).json()

    assert body["count"] == 3
    assert len(body["results"]) == 2
    assert body["next"] is not None


def test_history_requires_auth(anon_client):
    assert anon_client.get(URL).status_code == 401
