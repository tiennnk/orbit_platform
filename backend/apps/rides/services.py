from django.contrib.auth.models import AbstractBaseUser
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.drivers.models import Driver
from apps.drivers.selectors import find_nearby_drivers
from apps.rides.domain import (
    ACTIVE_RIDE_STATUSES,
    NoDriverAvailable,
    RideNotFound,
    RiderHasActiveRide,
)
from apps.rides.models import (
    DRIVER_ACTIVE_RIDE_CONSTRAINT,
    RIDER_ACTIVE_RIDE_CONSTRAINT,
    Ride,
)
from apps.rides.pricing import estimate_fare, estimate_road_distance_km
from apps.shared.db import violated_constraint
from apps.shared.geo import haversine_km

DISPATCH_RADIUS_KM = 5.0
DISPATCH_CANDIDATES = 10


def request_ride(
    *,
    rider: AbstractBaseUser,
    pickup_latitude: float,
    pickup_longitude: float,
    dropoff_latitude: float,
    dropoff_longitude: float,
) -> Ride:
    if Ride.objects.filter(rider=rider, status__in=ACTIVE_RIDE_STATUSES).exists():
        raise RiderHasActiveRide("You already have an active ride.")

    distance_km = estimate_road_distance_km(
        haversine_km(
            pickup_latitude, pickup_longitude, dropoff_latitude, dropoff_longitude
        )
    )
    own_driver_ids = frozenset(
        Driver.objects.filter(user=rider).values_list("id", flat=True)
    )
    candidates = find_nearby_drivers(
        latitude=pickup_latitude,
        longitude=pickup_longitude,
        radius_km=DISPATCH_RADIUS_KM,
        limit=DISPATCH_CANDIDATES,
        exclude_driver_ids=own_driver_ids,
    )

    for candidate in candidates:
        try:
            with transaction.atomic():
                driver = (
                    Driver.objects.select_for_update(skip_locked=True)
                    .filter(pk=candidate.driver.id)
                    .first()
                )
                if driver is None or not driver.can_accept_ride():
                    continue

                driver.start_trip()
                driver.save(update_fields=["availability", "updated_at"])
                return Ride.objects.create(
                    rider=rider,
                    driver=driver,
                    pickup_latitude=pickup_latitude,
                    pickup_longitude=pickup_longitude,
                    dropoff_latitude=dropoff_latitude,
                    dropoff_longitude=dropoff_longitude,
                    estimated_distance_km=round(distance_km, 3),
                    estimated_fare=estimate_fare(distance_km=distance_km),
                )
        except IntegrityError as exc:
            constraint = violated_constraint(exc)
            if constraint == RIDER_ACTIVE_RIDE_CONSTRAINT:
                raise RiderHasActiveRide("You already have an active ride.") from exc
            if constraint == DRIVER_ACTIVE_RIDE_CONSTRAINT:
                continue
            raise

    raise NoDriverAvailable("No driver is available near the pickup point.")


def _get_ride_for_update(ride_id: int) -> Ride:
    try:
        return (
            Ride.objects.select_for_update(of=("self",))
            .select_related("driver")
            .get(pk=ride_id)
        )
    except Ride.DoesNotExist as exc:
        raise RideNotFound(f"Ride {ride_id} not found.") from exc


def _release_driver(driver_id: int) -> None:
    driver = Driver.objects.select_for_update().get(pk=driver_id)
    driver.finish_trip()
    driver.save(update_fields=["availability", "updated_at"])


def start_ride(*, ride_id: int, user: AbstractBaseUser) -> Ride:
    with transaction.atomic():
        ride = _get_ride_for_update(ride_id)
        if ride.driver.user_id != user.pk:
            raise RideNotFound(f"Ride {ride_id} not found.")

        ride.start(timezone.now())
        ride.save(update_fields=["status", "started_at", "updated_at"])

    return ride


def complete_ride(*, ride_id: int, user: AbstractBaseUser) -> Ride:
    with transaction.atomic():
        ride = _get_ride_for_update(ride_id)
        if ride.driver.user_id != user.pk:
            raise RideNotFound(f"Ride {ride_id} not found.")

        ride.complete(timezone.now())
        ride.save(update_fields=["status", "completed_at", "updated_at"])
        _release_driver(ride.driver_id)

    return ride


def cancel_ride(*, ride_id: int, user: AbstractBaseUser) -> Ride:
    with transaction.atomic():
        ride = _get_ride_for_update(ride_id)
        if ride.rider_id != user.pk:
            raise RideNotFound(f"Ride {ride_id} not found.")

        ride.cancel(timezone.now())
        ride.save(update_fields=["status", "cancelled_at", "updated_at"])
        _release_driver(ride.driver_id)

    return ride
