import math
from dataclasses import dataclass

EARTH_RADIUS_KM = 6371.0088


@dataclass(frozen=True)
class BoundingBox:
    min_lat: float
    max_lat: float
    min_lng: float
    max_lng: float


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def bounding_box(lat: float, lng: float, radius_km: float) -> BoundingBox:
    angular = radius_km / EARTH_RADIUS_KM
    d_lat = math.degrees(angular)
    min_lat = lat - d_lat
    max_lat = lat + d_lat

    if min_lat <= -90.0 or max_lat >= 90.0:
        return BoundingBox(max(min_lat, -90.0), min(max_lat, 90.0), -180.0, 180.0)

    ratio = math.sin(angular) / math.cos(math.radians(lat))
    if ratio >= 1.0:
        return BoundingBox(min_lat, max_lat, -180.0, 180.0)

    d_lng = math.degrees(math.asin(ratio))
    min_lng, max_lng = lng - d_lng, lng + d_lng
    if min_lng < -180.0 or max_lng > 180.0:
        return BoundingBox(min_lat, max_lat, -180.0, 180.0)

    return BoundingBox(min_lat, max_lat, min_lng, max_lng)
