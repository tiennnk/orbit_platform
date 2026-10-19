import pytest
from django.utils import timezone

from apps.rides.domain import InvalidRideTransition, RideStatus
from apps.rides.models import Ride
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
