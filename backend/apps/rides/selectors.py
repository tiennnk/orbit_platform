from django.contrib.auth.models import AbstractBaseUser
from django.db.models import Q, QuerySet

from apps.drivers.models import Driver
from apps.rides.domain import (
    DRIVER_ACTIVE_STATUSES,
    RIDER_ACTIVE_STATUSES,
    RideNotFound,
    RideRole,
)
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
        .filter(
            Q(rider=user, status__in=RIDER_ACTIVE_STATUSES)
            | Q(driver__user=user, status__in=DRIVER_ACTIVE_STATUSES)
        )
        .order_by("-created_at")
        .first()
    )
    if ride is None:
        raise RideNotFound("You have no active ride.")
    return ride


def list_ride_history(*, user: AbstractBaseUser, role: str) -> QuerySet[Ride]:
    rides = Ride.objects.select_related("driver").order_by("-created_at", "-id")
    if role == RideRole.RIDER:
        return rides.filter(rider=user)

    driver_id = Driver.objects.filter(user=user).values_list("id", flat=True).first()
    if driver_id is None:
        return rides.none()
    return rides.filter(driver_id=driver_id)
