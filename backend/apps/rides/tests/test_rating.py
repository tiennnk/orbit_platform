from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.drivers.models import Driver
from apps.rides.domain import RATING_WINDOW, RideAlreadyRated, RideNotRatable
from apps.rides.models import Ride, RideRating
from apps.rides.services import complete_ride, rate_ride, start_ride
from apps.rides.tests.conftest import book
from conftest import _client_for

pytestmark = pytest.mark.django_db


def url(ride_id):
    return f"/api/v1/rides/{ride_id}/rating/"


@pytest.fixture
def finished(rider, place_driver):
    def _finish():
        driver = place_driver()
        ride = book(rider)
        start_ride(ride_id=ride.id, user=driver.user)
        return complete_ride(ride_id=ride.id, user=driver.user)

    return _finish


def test_rider_rates_completed_ride(rider_client, finished):
    ride = finished()

    response = rider_client.post(
        url(ride.id), {"score": 4, "comment": "Smooth trip"}, format="json"
    )

    assert response.status_code == 201
    assert response.json()["score"] == 4
    assert response.json()["comment"] == "Smooth trip"
    driver = Driver.objects.get(pk=ride.driver_id)
    assert driver.rating_count == 1
    assert driver.rating_average == 4


def test_comment_is_optional(rider_client, finished):
    ride = finished()

    response = rider_client.post(url(ride.id), {"score": 5}, format="json")

    assert response.status_code == 201
    assert response.json()["comment"] == ""


def test_same_driver_average(rider, rider_client, place_driver):
    driver = place_driver()
    for score in [5, 4, 3]:
        ride = book(rider)
        start_ride(ride_id=ride.id, user=driver.user)
        complete_ride(ride_id=ride.id, user=driver.user)
        rider_client.post(url(ride.id), {"score": score}, format="json")

    driver.refresh_from_db()
    assert driver.rating_count == 3
    assert driver.rating_total == 12
    assert driver.rating_average == 4


def test_cannot_rate_twice(rider, rider_client, finished):
    ride = finished()
    rate_ride(ride_id=ride.id, user=rider, score=5)

    response = rider_client.post(url(ride.id), {"score": 1}, format="json")

    assert response.status_code == 409
    assert Driver.objects.get(pk=ride.driver_id).rating_count == 1


def test_driver_cannot_rate_own_ride(finished):
    ride = finished()
    driver_client = _client_for(Driver.objects.get(pk=ride.driver_id).user)

    assert (
        driver_client.post(url(ride.id), {"score": 5}, format="json").status_code == 404
    )


def test_stranger_cannot_rate(other_client, finished):
    ride = finished()

    assert (
        other_client.post(url(ride.id), {"score": 5}, format="json").status_code == 404
    )


def test_cannot_rate_unfinished_ride(rider, rider_client, place_driver):
    place_driver()
    ride = book(rider)

    response = rider_client.post(url(ride.id), {"score": 5}, format="json")

    assert response.status_code == 409


def test_cannot_rate_after_window(rider, finished):
    ride = finished()
    Ride.objects.filter(pk=ride.id).update(
        completed_at=timezone.now() - RATING_WINDOW - timedelta(minutes=1)
    )

    with pytest.raises(RideNotRatable):
        rate_ride(ride_id=ride.id, user=rider, score=5)


@pytest.mark.parametrize("score", [0, 6, "great"])
def test_invalid_score_returns_400(rider_client, finished, score):
    ride = finished()

    response = rider_client.post(url(ride.id), {"score": score}, format="json")

    assert response.status_code == 400
    assert "score" in response.json()


def test_long_comment_returns_400(rider_client, finished):
    ride = finished()

    response = rider_client.post(
        url(ride.id), {"score": 5, "comment": "x" * 501}, format="json"
    )

    assert response.status_code == 400


def test_rating_shows_in_rider_history_only(rider, rider_client, finished):
    ride = finished()
    rate_ride(ride_id=ride.id, user=rider, score=3, comment="Late")
    driver_client = _client_for(Driver.objects.get(pk=ride.driver_id).user)

    rider_view = rider_client.get("/api/v1/rides/history/").json()["results"][0]
    driver_view = driver_client.get("/api/v1/rides/history/?role=driver").json()[
        "results"
    ][0]

    assert rider_view["rating"]["score"] == 3
    assert driver_view["rating"] is None
    assert rider_client.get(f"/api/v1/rides/{ride.id}/").json()["rating"]["score"] == 3
    assert driver_client.get(f"/api/v1/rides/{ride.id}/").json()["rating"] is None


def test_driver_sees_own_average(rider, finished):
    ride = finished()
    rate_ride(ride_id=ride.id, user=rider, score=4)
    driver_client = _client_for(Driver.objects.get(pk=ride.driver_id).user)

    body = driver_client.get("/api/v1/drivers/me/").json()

    assert body["rating_average"] == 4
    assert body["rating_count"] == 1


def test_rider_sees_driver_average_on_ride(rider, rider_client, place_driver):
    driver = place_driver()
    Driver.objects.filter(pk=driver.pk).update(rating_count=2, rating_total=9)
    book(rider)

    body = rider_client.get("/api/v1/rides/current/").json()

    assert body["driver"]["rating_average"] == 4.5
    assert body["driver"]["rating_count"] == 2


def test_new_driver_has_no_average(place_driver):
    assert place_driver().rating_average is None


def test_add_rating_rejects_out_of_range(place_driver):
    driver = place_driver()

    with pytest.raises(ValueError):
        driver.add_rating(6)


def test_db_rejects_total_out_of_range(place_driver):
    driver = place_driver()

    with pytest.raises(IntegrityError), transaction.atomic():
        Driver.objects.filter(pk=driver.pk).update(rating_count=1, rating_total=6)


def test_db_rejects_score_out_of_range(rider, finished):
    ride = finished()

    with pytest.raises(IntegrityError), transaction.atomic():
        RideRating.objects.create(ride=ride, driver_id=ride.driver_id, score=0)


def test_already_rated_error_type(rider, finished):
    ride = finished()
    rate_ride(ride_id=ride.id, user=rider, score=5)

    with pytest.raises(RideAlreadyRated):
        rate_ride(ride_id=ride.id, user=rider, score=5)
