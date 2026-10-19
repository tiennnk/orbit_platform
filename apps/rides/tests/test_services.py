import threading

import pytest
from django.db import IntegrityError, connection, transaction

from apps.drivers.domain import Availability
from apps.drivers.models import Driver
from apps.rides.domain import (
    InvalidRideTransition,
    NoDriverAvailable,
    RideNotFound,
    RiderHasActiveRide,
    RideStatus,
)
from apps.rides.models import Ride
from apps.rides.pricing import ROAD_DISTANCE_FACTOR, estimate_fare
from apps.rides.services import cancel_ride, complete_ride, request_ride, start_ride
from apps.rides.tests.conftest import DROPOFF, PICKUP
from apps.shared.geo import haversine_km


def request(rider) -> Ride:
    return request_ride(
        rider=rider,
        pickup_latitude=PICKUP[0],
        pickup_longitude=PICKUP[1],
        dropoff_latitude=DROPOFF[0],
        dropoff_longitude=DROPOFF[1],
    )


@pytest.mark.django_db
class TestRequestRide:
    def test_assigns_nearest_driver_and_marks_them_busy(self, rider, place_driver):
        place_driver(2.0)
        nearest = place_driver(0.3)

        ride = request(rider)

        assert ride.driver_id == nearest.id
        assert ride.status == RideStatus.ASSIGNED
        nearest.refresh_from_db()
        assert nearest.availability == Availability.ON_TRIP

    def test_stores_distance_and_fare(self, rider, place_driver):
        place_driver()

        ride = request(rider)

        expected_km = haversine_km(*PICKUP, *DROPOFF) * ROAD_DISTANCE_FACTOR
        assert ride.estimated_distance_km == pytest.approx(expected_km, abs=0.001)
        assert ride.estimated_fare == estimate_fare(distance_km=expected_km)

    def test_skips_driver_who_is_already_busy(self, rider, other_user, place_driver):
        nearest = place_driver(0.2)
        second = place_driver(1.0)
        request(other_user)

        ride = request(rider)

        assert ride.driver_id == second.id
        assert Ride.objects.get(rider=other_user).driver_id == nearest.id

    def test_no_driver_nearby_raises_and_creates_nothing(self, rider, place_driver):
        place_driver(km_north=50)

        with pytest.raises(NoDriverAvailable):
            request(rider)

        assert not Ride.objects.exists()

    def test_rider_cannot_have_two_active_rides(self, rider, place_driver):
        place_driver(0.2)
        place_driver(0.4)
        request(rider)

        with pytest.raises(RiderHasActiveRide):
            request(rider)

        assert Ride.objects.count() == 1

    def test_rider_is_never_matched_with_their_own_driver_profile(
        self, rider, place_driver
    ):
        place_driver(0.1, user=rider)
        other = place_driver(1.0)

        assert request(rider).driver_id == other.id

    def test_database_allows_one_active_ride_per_driver(
        self, rider, other_user, place_driver
    ):
        place_driver()
        ride = request(rider)

        with pytest.raises(IntegrityError), transaction.atomic():
            Ride.objects.create(
                rider=other_user,
                driver=ride.driver,
                pickup_latitude=PICKUP[0],
                pickup_longitude=PICKUP[1],
                dropoff_latitude=DROPOFF[0],
                dropoff_longitude=DROPOFF[1],
                estimated_distance_km=1,
                estimated_fare=15_000,
            )


@pytest.mark.django_db(transaction=True)
def test_dispatch_skips_driver_locked_by_another_request(rider, place_driver):
    locked = place_driver(0.2)
    free = place_driver(1.0)
    lock_taken = threading.Event()
    release = threading.Event()

    def hold_lock():
        try:
            with transaction.atomic():
                Driver.objects.select_for_update().get(pk=locked.pk)
                lock_taken.set()
                release.wait(timeout=10)
        finally:
            connection.close()

    holder = threading.Thread(target=hold_lock)
    holder.start()
    assert lock_taken.wait(timeout=10)
    try:
        ride = request(rider)
    finally:
        release.set()
        holder.join()

    assert ride.driver_id == free.id


@pytest.mark.django_db
class TestRideLifecycle:
    def test_driver_starts_and_completes_ride(self, rider, place_driver):
        driver = place_driver()
        ride = request(rider)

        start_ride(ride_id=ride.id, user=driver.user)
        ride = complete_ride(ride_id=ride.id, user=driver.user)

        assert ride.status == RideStatus.COMPLETED
        driver.refresh_from_db()
        assert driver.can_accept_ride()

    def test_rider_cancels_assigned_ride_and_driver_is_released(
        self, rider, place_driver
    ):
        driver = place_driver()
        ride = request(rider)

        ride = cancel_ride(ride_id=ride.id, user=rider)

        assert ride.status == RideStatus.CANCELLED
        driver.refresh_from_db()
        assert driver.availability == Availability.AVAILABLE

    def test_cannot_cancel_ride_in_progress(self, rider, place_driver):
        driver = place_driver()
        ride = request(rider)
        start_ride(ride_id=ride.id, user=driver.user)

        with pytest.raises(InvalidRideTransition):
            cancel_ride(ride_id=ride.id, user=rider)

    def test_only_assigned_driver_can_start(self, rider, other_user, place_driver):
        place_driver()
        ride = request(rider)

        with pytest.raises(RideNotFound):
            start_ride(ride_id=ride.id, user=other_user)

    def test_only_rider_can_cancel(self, rider, place_driver):
        driver = place_driver()
        ride = request(rider)

        with pytest.raises(RideNotFound):
            cancel_ride(ride_id=ride.id, user=driver.user)

    def test_rider_can_request_again_after_completion(self, rider, place_driver):
        driver = place_driver()
        ride = request(rider)
        start_ride(ride_id=ride.id, user=driver.user)
        complete_ride(ride_id=ride.id, user=driver.user)

        assert request(rider).driver_id == driver.id
