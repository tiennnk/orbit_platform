import heapq
from dataclasses import dataclass
from datetime import timedelta

from django.contrib.auth.models import AbstractBaseUser
from django.db.models import QuerySet
from django.utils import timezone

from apps.drivers.domain import ApprovalStatus, Availability, DriverNotFound
from apps.drivers.models import Driver, DriverLocation
from apps.shared.geo import bounding_box, haversine_km

LOCATION_MAX_AGE = timedelta(seconds=60)


@dataclass(frozen=True)
class NearbyDriver:
    driver: Driver
    latitude: float
    longitude: float
    distance_km: float


def get_driver_by_id(*, driver_id: int) -> Driver:
    try:
        return Driver.objects.get(pk=driver_id)
    except Driver.DoesNotExist as exc:
        raise DriverNotFound(f"Driver {driver_id} not found.") from exc


def get_driver_for_user(*, user: AbstractBaseUser) -> Driver:
    try:
        return Driver.objects.get(user=user)
    except Driver.DoesNotExist as exc:
        raise DriverNotFound("This account has no driver profile.") from exc


def nearby_candidates_queryset(
    *, latitude: float, longitude: float, radius_km: float
) -> QuerySet[DriverLocation]:
    box = bounding_box(latitude, longitude, radius_km)
    return DriverLocation.objects.select_related("driver").filter(
        latitude__range=(box.min_lat, box.max_lat),
        longitude__range=(box.min_lng, box.max_lng),
        updated_at__gte=timezone.now() - LOCATION_MAX_AGE,
        driver__approval_status=ApprovalStatus.APPROVED,
        driver__is_online=True,
        driver__availability=Availability.AVAILABLE,
    )


def find_nearby_drivers(
    *,
    latitude: float,
    longitude: float,
    radius_km: float = 3.0,
    limit: int = 10,
    exclude_driver_ids: frozenset[int] = frozenset(),
) -> list[NearbyDriver]:
    candidates = nearby_candidates_queryset(
        latitude=latitude, longitude=longitude, radius_km=radius_km
    )
    if exclude_driver_ids:
        candidates = candidates.exclude(driver_id__in=exclude_driver_ids)

    within_radius = (
        NearbyDriver(
            driver=location.driver,
            latitude=location.latitude,
            longitude=location.longitude,
            distance_km=distance,
        )
        for location in candidates
        if (
            distance := haversine_km(
                latitude, longitude, location.latitude, location.longitude
            )
        )
        <= radius_km
    )
    return heapq.nsmallest(
        limit, within_radius, key=lambda n: (n.distance_km, n.driver.id)
    )
