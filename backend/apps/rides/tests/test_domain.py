from datetime import timedelta

import pytest
from django.utils import timezone

from apps.drivers.models import Driver
from apps.rides.domain import InvalidRideTransition, OfferStatus, RideStatus
from apps.rides.models import Ride, RideOffer
from apps.rides.pricing import MINIMUM_FARE_VND, estimate_fare


def make_ride(status=RideStatus.ASSIGNED) -> Ride:
    return Ride(status=status)


def test_assigned_ride_can_start():
    ride = make_ride()
    now = timezone.now()

    ride.start(now)

    assert ride.status == RideStatus.IN_PROGRESS
    assert ride.started_at == now


def test_ride_in_progress_can_complete():
    ride = make_ride(RideStatus.IN_PROGRESS)

    ride.complete(timezone.now())

    assert ride.status == RideStatus.COMPLETED
    assert ride.completed_at is not None
    assert ride.is_active is False


def test_assigned_ride_can_be_cancelled():
    ride = make_ride()

    ride.cancel(timezone.now())

    assert ride.status == RideStatus.CANCELLED


@pytest.mark.parametrize(
    "status, action",
    [
        (RideStatus.IN_PROGRESS, "start"),
        (RideStatus.COMPLETED, "start"),
        (RideStatus.ASSIGNED, "complete"),
        (RideStatus.CANCELLED, "complete"),
        (RideStatus.IN_PROGRESS, "cancel"),
        (RideStatus.COMPLETED, "cancel"),
        (RideStatus.NO_DRIVER, "cancel"),
        (RideStatus.SEARCHING, "start"),
    ],
)
def test_invalid_transitions_raise(status, action):
    ride = make_ride(status)

    with pytest.raises(InvalidRideTransition):
        getattr(ride, action)(timezone.now())

    assert ride.status == status


def test_short_trip_pays_minimum_fare():
    assert estimate_fare(distance_km=0.3) == MINIMUM_FARE_VND


def test_fare_is_rounded_up_to_thousand_vnd():
    assert estimate_fare(distance_km=2.1) == 22_000


def test_fare_grows_with_distance():
    assert estimate_fare(distance_km=10) > estimate_fare(distance_km=5)


def test_new_ride_is_searching():
    assert Ride().status == RideStatus.SEARCHING


def test_searching_ride_can_be_assigned():
    ride = make_ride(RideStatus.SEARCHING)
    driver = Driver(full_name="A", phone="1")
    now = timezone.now()

    ride.assign(driver, now)

    assert ride.status == RideStatus.ASSIGNED
    assert ride.driver is driver
    assert ride.assigned_at == now


def test_searching_ride_can_give_up():
    ride = make_ride(RideStatus.SEARCHING)
    ride.give_up()
    assert ride.status == RideStatus.NO_DRIVER
    assert ride.is_active is False


def test_searching_ride_can_be_cancelled():
    ride = make_ride(RideStatus.SEARCHING)
    ride.cancel(timezone.now())
    assert ride.status == RideStatus.CANCELLED


@pytest.mark.parametrize("status", [RideStatus.ASSIGNED, RideStatus.NO_DRIVER])
def test_only_searching_ride_can_be_assigned(status):
    with pytest.raises(InvalidRideTransition):
        make_ride(status).assign(Driver(), timezone.now())


def test_offer_can_only_be_answered_once():
    offer = RideOffer(status=OfferStatus.PENDING)
    offer.accept(timezone.now())

    with pytest.raises(InvalidRideTransition):
        offer.decline(timezone.now())
    assert offer.status == OfferStatus.ACCEPTED


def test_offer_expiry():
    now = timezone.now()
    offer = RideOffer(expires_at=now)
    assert offer.is_expired(now) is True
    assert offer.is_expired(now - timedelta(seconds=1)) is False
