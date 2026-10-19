import math

import pytest

from apps.shared.geo import EARTH_RADIUS_KM, bounding_box, haversine_km

HCMC = (10.7769, 106.7009)
HANOI = (21.0285, 105.8542)


def destination(lat: float, lng: float, bearing_deg: float, distance_km: float):
    phi1, lambda1 = math.radians(lat), math.radians(lng)
    theta = math.radians(bearing_deg)
    delta = distance_km / EARTH_RADIUS_KM
    phi2 = math.asin(
        math.sin(phi1) * math.cos(delta)
        + math.cos(phi1) * math.sin(delta) * math.cos(theta)
    )
    lambda2 = lambda1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(phi1),
        math.cos(delta) - math.sin(phi1) * math.sin(phi2),
    )
    return math.degrees(phi2), (math.degrees(lambda2) + 540) % 360 - 180


def test_distance_to_same_point_is_zero():
    assert haversine_km(*HCMC, *HCMC) == 0


def test_hcmc_to_hanoi():
    assert haversine_km(*HCMC, *HANOI) == pytest.approx(1143.5, abs=1)


def test_distance_is_symmetric():
    assert haversine_km(*HCMC, *HANOI) == pytest.approx(haversine_km(*HANOI, *HCMC))


def test_one_degree_of_latitude():
    assert haversine_km(0, 0, 1, 0) == pytest.approx(111.19, abs=0.01)


@pytest.mark.parametrize("lat", [0.0, 10.77, -33.9, 60.0, 80.0])
@pytest.mark.parametrize("radius_km", [0.5, 3.0, 25.0])
def test_bounding_box_contains_every_point_on_the_circle(lat, radius_km):
    lng = 106.7
    box = bounding_box(lat, lng, radius_km)

    for bearing in range(0, 360, 5):
        p_lat, p_lng = destination(lat, lng, bearing, radius_km * 0.999999)
        assert box.min_lat <= p_lat <= box.max_lat
        assert box.min_lng <= p_lng <= box.max_lng


def test_bounding_box_is_tight_at_the_equator():
    box = bounding_box(0.0, 0.0, 111.19)

    assert box.max_lat == pytest.approx(1.0, abs=0.01)
    assert box.max_lng == pytest.approx(1.0, abs=0.01)


def test_bounding_box_near_pole_covers_all_longitudes():
    box = bounding_box(89.99, 10.0, 5.0)

    assert (box.min_lng, box.max_lng) == (-180.0, 180.0)
    assert box.max_lat == 90.0


def test_bounding_box_crossing_antimeridian_covers_all_longitudes():
    box = bounding_box(0.0, 179.99, 5.0)

    assert (box.min_lng, box.max_lng) == (-180.0, 180.0)
