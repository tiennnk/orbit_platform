from django.contrib.auth.models import AbstractBaseUser
from django.db.models import Q

from apps.rides.domain import ACTIVE_RIDE_STATUSES, RideNotFound
from apps.rides.models import Ride


def get_ride_for_participant(*, ride_id: int, user: AbstractBaseUser) -> Ride:
    try:
        return (
            Ride.objects.select_related("driver")
            .filter(Q(rider=user) | Q(driver__user=user))
            .get(pk=ride_id)
        )
    except Ride.DoesNotExist as exc:
        raise RideNotFound(f"Ride {ride_id} not found.") from exc


def get_current_ride(*, user: AbstractBaseUser) -> Ride:
    ride = (
        Ride.objects.select_related("driver")
        .filter(Q(rider=user) | Q(driver__user=user), status__in=ACTIVE_RIDE_STATUSES)
        .order_by("-created_at")
        .first()
    )
    if ride is None:
        raise RideNotFound("You have no active ride.")
    return ride
