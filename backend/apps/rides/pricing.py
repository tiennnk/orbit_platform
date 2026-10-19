import math

BASE_FARE_VND = 12_000
PER_KM_VND = 4_500
MINIMUM_FARE_VND = 15_000
ROAD_DISTANCE_FACTOR = 1.3


def estimate_road_distance_km(straight_line_km: float) -> float:
    return straight_line_km * ROAD_DISTANCE_FACTOR


def estimate_fare(*, distance_km: float) -> int:
    raw = BASE_FARE_VND + PER_KM_VND * distance_km
    rounded = math.ceil(raw / 1000) * 1000
    return max(MINIMUM_FARE_VND, rounded)
