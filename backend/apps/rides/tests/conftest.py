from itertools import count

import pytest
from django.utils import timezone

from apps.drivers.domain import ApprovalStatus
from apps.drivers.models import Driver, DriverLocation
from apps.rides.domain import OfferStatus
from apps.rides.services import accept_offer, request_ride
from conftest import _client_for

PICKUP = (10.7769, 106.7009)
DROPOFF = (10.8231, 106.6297)
KM_IN_LAT_DEGREES = 1 / 111.19

_sequence = count()


@pytest.fixture
def rider(django_user_model):
    return django_user_model.objects.create_user(username="rider1")


@pytest.fixture
def rider_client(rider):
    return _client_for(rider)


@pytest.fixture
def place_driver(django_user_model):
    def _place(km_north: float = 0.5, user=None) -> Driver:
        n = next(_sequence)
        if user is None:
            user = django_user_model.objects.create_user(username=f"ridedriver{n}")
        driver = Driver.objects.create(
            user=user,
            full_name=f"Driver {n}",
            phone=f"07{n:08d}",
            approval_status=ApprovalStatus.APPROVED,
            is_online=True,
        )
        DriverLocation.objects.create(
            driver=driver,
            latitude=PICKUP[0] + km_north * KM_IN_LAT_DEGREES,
            longitude=PICKUP[1],
            recorded_at=timezone.now(),
        )
        return driver

    return _place


@pytest.fixture
def ride_payload():
    return {
        "pickup_latitude": PICKUP[0],
        "pickup_longitude": PICKUP[1],
        "dropoff_latitude": DROPOFF[0],
        "dropoff_longitude": DROPOFF[1],
    }


def request(rider):
    return request_ride(
        rider=rider,
        pickup_latitude=PICKUP[0],
        pickup_longitude=PICKUP[1],
        dropoff_latitude=DROPOFF[0],
        dropoff_longitude=DROPOFF[1],
    )


def pending_offer(ride):
    return ride.offers.select_related("driver__user").get(status=OfferStatus.PENDING)


def book(rider):
    ride = request(rider)
    offer = pending_offer(ride)
    return accept_offer(offer_id=offer.id, user=offer.driver.user)
