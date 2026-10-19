import threading
from datetime import timedelta

import pytest
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.drivers.domain import Availability
from apps.drivers.models import Driver
from apps.drivers.services import go_offline
from apps.rides.domain import (
    InvalidRideTransition,
    NoDriverAvailable,
    OfferNoLongerAvailable,
    OfferNotFound,
    OfferStatus,
    RideNotFound,
    RiderHasActiveRide,
    RideStatus,
)
from apps.rides.models import Ride, RideOffer
from apps.rides.pricing import ROAD_DISTANCE_FACTOR, estimate_fare
from apps.rides.services import (
    OFFER_TTL,
    SEARCH_TIMEOUT,
    accept_offer,
    advance_dispatch,
    cancel_ride,
    complete_ride,
    decline_offer,
    get_current_offer,
    start_ride,
)
from apps.rides.tests.conftest import DROPOFF, PICKUP, book, pending_offer, request
from apps.shared.geo import haversine_km


@pytest.mark.django_db
class TestRequestRide:
    def test_offers_ride_to_nearest_driver(self, rider, place_driver):
        place_driver(2.0)
        nearest = place_driver(0.3)

        ride = request(rider)

        assert ride.status == RideStatus.SEARCHING
        assert ride.driver is None
        offer = pending_offer(ride)
        assert offer.driver_id == nearest.id
        nearest.refresh_from_db()
        assert nearest.availability == Availability.AVAILABLE

    def test_stores_distance_and_fare(self, rider, place_driver):
        place_driver()

        ride = request(rider)

        expected_km = haversine_km(*PICKUP, *DROPOFF) * ROAD_DISTANCE_FACTOR
        assert ride.estimated_distance_km == pytest.approx(expected_km, abs=0.001)
        assert ride.estimated_fare == estimate_fare(distance_km=expected_km)

    def test_no_driver_nearby_raises_and_creates_nothing(self, rider, place_driver):
        place_driver(km_north=50)

        with pytest.raises(NoDriverAvailable):
            request(rider)

        assert not Ride.objects.exists()

    def test_searching_ride_counts_as_active(self, rider, place_driver):
        place_driver(0.2)
        place_driver(0.4)
        request(rider)

        with pytest.raises(RiderHasActiveRide):
            request(rider)

    def test_rider_is_never_offered_to_their_own_driver_profile(
        self, rider, place_driver
    ):
        place_driver(0.1, user=rider)
        other = place_driver(1.0)

        assert pending_offer(request(rider)).driver_id == other.id

    def test_driver_with_pending_offer_is_not_offered_another_ride(
        self, rider, other_user, place_driver
    ):
        first = place_driver(0.2)
        second = place_driver(1.0)

        request(other_user)
        ride = request(rider)

        assert pending_offer(ride).driver_id == second.id
        assert RideOffer.objects.get(driver=first).status == OfferStatus.PENDING

    def test_only_driver_busy_with_offer_means_no_driver(
        self, rider, other_user, place_driver
    ):
        place_driver()
        request(other_user)

        with pytest.raises(NoDriverAvailable):
            request(rider)


@pytest.mark.django_db
class TestOffers:
    def test_accept_assigns_ride_and_marks_driver_busy(self, rider, place_driver):
        driver = place_driver()
        ride = request(rider)

        ride = accept_offer(offer_id=pending_offer(ride).id, user=driver.user)

        assert ride.status == RideStatus.ASSIGNED
        assert ride.driver_id == driver.id
        assert ride.assigned_at is not None
        driver.refresh_from_db()
        assert driver.availability == Availability.ON_TRIP

    def test_decline_moves_offer_to_next_driver(self, rider, place_driver):
        first = place_driver(0.2)
        second = place_driver(1.0)
        ride = request(rider)

        decline_offer(offer_id=pending_offer(ride).id, user=first.user)

        assert pending_offer(ride).driver_id == second.id
        assert RideOffer.objects.get(driver=first).status == OfferStatus.DECLINED

    def test_last_driver_declining_ends_search(self, rider, place_driver):
        driver = place_driver()
        ride = request(rider)

        decline_offer(offer_id=pending_offer(ride).id, user=driver.user)

        ride.refresh_from_db()
        assert ride.status == RideStatus.NO_DRIVER

    def test_expired_offer_moves_to_next_driver(self, rider, place_driver):
        first = place_driver(0.2)
        second = place_driver(1.0)
        ride = request(rider)

        advance_dispatch(ride_id=ride.id, now=timezone.now() + OFFER_TTL)

        assert RideOffer.objects.get(driver=first).status == OfferStatus.EXPIRED
        assert pending_offer(ride).driver_id == second.id

    def test_offer_still_valid_is_left_alone(self, rider, place_driver):
        driver = place_driver()
        ride = request(rider)

        advance_dispatch(ride_id=ride.id)

        assert pending_offer(ride).driver_id == driver.id

    def test_accepting_expired_offer_fails(self, rider, place_driver):
        driver = place_driver()
        ride = request(rider)
        RideOffer.objects.filter(ride=ride).update(expires_at=timezone.now())

        with pytest.raises(OfferNoLongerAvailable):
            accept_offer(offer_id=pending_offer(ride).id, user=driver.user)

    def test_search_gives_up_after_timeout(self, rider, place_driver):
        place_driver(0.2)
        place_driver(1.0)
        ride = request(rider)

        ride = advance_dispatch(
            ride_id=ride.id, now=ride.created_at + SEARCH_TIMEOUT + OFFER_TTL
        )

        assert ride.status == RideStatus.NO_DRIVER

    def test_driver_cannot_answer_someone_elses_offer(
        self, rider, other_user, place_driver
    ):
        place_driver()
        ride = request(rider)

        with pytest.raises(OfferNotFound):
            accept_offer(offer_id=pending_offer(ride).id, user=other_user)

    def test_driver_who_went_offline_cannot_accept(self, rider, place_driver):
        driver = place_driver()
        ride = request(rider)
        go_offline(driver_id=driver.id)

        with pytest.raises(OfferNoLongerAvailable):
            accept_offer(offer_id=pending_offer(ride).id, user=driver.user)

    def test_offer_cannot_be_answered_twice(self, rider, place_driver):
        driver = place_driver()
        ride = request(rider)
        offer = pending_offer(ride)
        accept_offer(offer_id=offer.id, user=driver.user)

        with pytest.raises(OfferNoLongerAvailable):
            decline_offer(offer_id=offer.id, user=driver.user)

    def test_current_offer_for_driver(self, rider, place_driver):
        driver = place_driver()
        ride = request(rider)

        assert get_current_offer(user=driver.user).ride_id == ride.id

    def test_current_offer_expires_lazily(self, rider, place_driver):
        first = place_driver(0.2)
        second = place_driver(1.0)
        ride = request(rider)
        RideOffer.objects.filter(ride=ride).update(expires_at=timezone.now())

        with pytest.raises(OfferNotFound):
            get_current_offer(user=first.user)

        assert get_current_offer(user=second.user).ride_id == ride.id

    def test_rider_cancels_while_searching(self, rider, place_driver):
        driver = place_driver()
        ride = request(rider)

        ride = cancel_ride(ride_id=ride.id, user=rider)

        assert ride.status == RideStatus.CANCELLED
        assert RideOffer.objects.get(driver=driver).status == OfferStatus.EXPIRED

    def test_database_allows_one_pending_offer_per_driver(
        self, rider, other_user, place_driver
    ):
        driver = place_driver()
        request(rider)
        other_ride = Ride.objects.create(
            rider=other_user,
            pickup_latitude=PICKUP[0],
            pickup_longitude=PICKUP[1],
            dropoff_latitude=DROPOFF[0],
            dropoff_longitude=DROPOFF[1],
            estimated_distance_km=1,
            estimated_fare=15_000,
        )

        with pytest.raises(IntegrityError), transaction.atomic():
            RideOffer.objects.create(
                ride=other_ride,
                driver=driver,
                expires_at=timezone.now() + timedelta(seconds=15),
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

    assert pending_offer(ride).driver_id == free.id


@pytest.mark.django_db
class TestRideLifecycle:
    def test_full_trip_releases_driver(self, rider, place_driver):
        driver = place_driver()
        ride = book(rider)

        start_ride(ride_id=ride.id, user=driver.user)
        ride = complete_ride(ride_id=ride.id, user=driver.user)

        assert ride.status == RideStatus.COMPLETED
        driver.refresh_from_db()
        assert driver.can_accept_ride()

    def test_rider_cancels_assigned_ride_and_driver_is_released(
        self, rider, place_driver
    ):
        driver = place_driver()
        ride = book(rider)

        ride = cancel_ride(ride_id=ride.id, user=rider)

        assert ride.status == RideStatus.CANCELLED
        driver.refresh_from_db()
        assert driver.availability == Availability.AVAILABLE

    def test_cannot_cancel_ride_in_progress(self, rider, place_driver):
        driver = place_driver()
        ride = book(rider)
        start_ride(ride_id=ride.id, user=driver.user)

        with pytest.raises(InvalidRideTransition):
            cancel_ride(ride_id=ride.id, user=rider)

    def test_only_assigned_driver_can_start(self, rider, other_user, place_driver):
        place_driver()
        ride = book(rider)

        with pytest.raises(RideNotFound):
            start_ride(ride_id=ride.id, user=other_user)

    def test_offered_driver_cannot_start_before_accepting(self, rider, place_driver):
        driver = place_driver()
        ride = request(rider)

        with pytest.raises(RideNotFound):
            start_ride(ride_id=ride.id, user=driver.user)

    def test_only_rider_can_cancel(self, rider, place_driver):
        driver = place_driver()
        ride = book(rider)

        with pytest.raises(RideNotFound):
            cancel_ride(ride_id=ride.id, user=driver.user)

    def test_rider_can_request_again_after_completion(self, rider, place_driver):
        driver = place_driver()
        ride = book(rider)
        start_ride(ride_id=ride.id, user=driver.user)
        complete_ride(ride_id=ride.id, user=driver.user)

        assert pending_offer(request(rider)).driver_id == driver.id

    def test_database_allows_one_active_ride_per_driver(
        self, rider, other_user, place_driver
    ):
        place_driver()
        ride = book(rider)

        with pytest.raises(IntegrityError), transaction.atomic():
            Ride.objects.create(
                rider=other_user,
                driver=ride.driver,
                status=RideStatus.ASSIGNED,
                assigned_at=timezone.now(),
                pickup_latitude=PICKUP[0],
                pickup_longitude=PICKUP[1],
                dropoff_latitude=DROPOFF[0],
                dropoff_longitude=DROPOFF[1],
                estimated_distance_km=1,
                estimated_fare=15_000,
            )

    def test_database_requires_driver_once_assigned(self, rider):
        with pytest.raises(IntegrityError), transaction.atomic():
            Ride.objects.create(
                rider=rider,
                status=RideStatus.ASSIGNED,
                pickup_latitude=PICKUP[0],
                pickup_longitude=PICKUP[1],
                dropoff_latitude=DROPOFF[0],
                dropoff_longitude=DROPOFF[1],
                estimated_distance_km=1,
                estimated_fare=15_000,
            )
