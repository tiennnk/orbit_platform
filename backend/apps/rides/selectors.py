from dataclasses import dataclass
from datetime import datetime

from django.contrib.auth.models import AbstractBaseUser
from django.db.models import Q, QuerySet

from apps.drivers.models import Driver, DriverLocation
from apps.rides.domain import (
    DRIVER_ACTIVE_STATUSES,
    RIDER_ACTIVE_STATUSES,
    DriverLocationUnavailable,
    RideNotFound,
    RideRole,
    RideStatus,
)
from apps.rides.models import Ride
from apps.rides.pricing import estimate_eta_minutes, estimate_road_distance_km
from apps.shared.geo import haversine_km


@dataclass(frozen=True)
class DriverPosition:
    latitude: float
    longitude: float
    recorded_at: datetime
    heading_to: str
    distance_km: float
    eta_minutes: int


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


def get_driver_position(*, ride_id: int, user: AbstractBaseUser) -> DriverPosition:
    ride = Ride.objects.filter(pk=ride_id, rider=user).first()
    if ride is None:
        raise RideNotFound(f"Ride {ride_id} not found.")
    if ride.status not in DRIVER_ACTIVE_STATUSES:
        raise DriverLocationUnavailable("This ride has no driver on the way.")

    location = DriverLocation.objects.filter(driver_id=ride.driver_id).first()
    if location is None:
        raise DriverLocationUnavailable("The driver has not shared a location yet.")

    if ride.status == RideStatus.ASSIGNED:
        heading_to = "pickup"
        target = (ride.pickup_latitude, ride.pickup_longitude)
    else:
        heading_to = "dropoff"
        target = (ride.dropoff_latitude, ride.dropoff_longitude)

    distance_km = estimate_road_distance_km(
        haversine_km(location.latitude, location.longitude, *target)
    )
    return DriverPosition(
        latitude=location.latitude,
        longitude=location.longitude,
        recorded_at=location.recorded_at,
        heading_to=heading_to,
        distance_km=round(distance_km, 2),
        eta_minutes=estimate_eta_minutes(distance_km=distance_km),
    )
