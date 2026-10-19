from urllib.error import URLError

import pytest

from apps.places import services

pytestmark = pytest.mark.django_db

URL = "/api/v1/places/search/"


def feature(lng, lat, **props):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
        "properties": {"countrycode": "VN", "country": "Việt Nam", **props},
    }


TAN_BINH = feature(
    106.6412817,
    10.7995218,
    name="Tân Bình",
    city="Thành phố Hồ Chí Minh",
)


@pytest.fixture
def geocoder(monkeypatch):
    calls = []

    def fake_fetch(params):
        calls.append(params)
        return {"type": "FeatureCollection", "features": fake_fetch.results}

    fake_fetch.results = [TAN_BINH]
    fake_fetch.calls = calls
    monkeypatch.setattr(services, "_fetch", fake_fetch)
    return fake_fetch


def test_search_returns_places(user_client, geocoder):
    response = user_client.get(URL, {"q": "Tân Bình"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "Tân Bình",
            "address": "Thành phố Hồ Chí Minh, Việt Nam",
            "latitude": 10.7995218,
            "longitude": 106.6412817,
        }
    ]
    assert geocoder.calls[0] == {"q": "tân bình", "limit": "15"}


def test_address_includes_street_and_skips_repeats(user_client, geocoder):
    geocoder.results = [
        feature(
            106.67,
            10.75,
            name="Tân Bình",
            housenumber="407A",
            street="Nguyễn Trãi",
            district="An Đông",
            city="Thành phố Hồ Chí Minh",
            state="Thành phố Hồ Chí Minh",
        )
    ]

    body = user_client.get(URL, {"q": "tan binh"}).json()

    assert body[0]["address"] == (
        "407A Nguyễn Trãi, An Đông, Thành phố Hồ Chí Minh, Việt Nam"
    )


def test_name_falls_back_to_address(user_client, geocoder):
    geocoder.results = [feature(106.70, 10.77, housenumber="12", street="Nguyễn Huệ")]

    body = user_client.get(URL, {"q": "12 nguyen hue"}).json()

    assert body[0]["name"] == "12 Nguyễn Huệ"


def test_results_outside_allowed_countries_are_dropped(user_client, geocoder):
    geocoder.results = [
        feature(100.5, 13.7, name="Bangkok", countrycode="TH"),
        TAN_BINH,
    ]

    body = user_client.get(URL, {"q": "tan binh"}).json()

    assert [place["name"] for place in body] == ["Tân Bình"]


def test_duplicate_results_are_merged(user_client, geocoder):
    geocoder.results = [TAN_BINH, TAN_BINH]

    assert len(user_client.get(URL, {"q": "tan binh"}).json()) == 1


def test_results_are_capped(user_client, geocoder):
    geocoder.results = [feature(106.7, 10.7, name=f"Place {n}") for n in range(15)]

    assert len(user_client.get(URL, {"q": "place"}).json()) == services.MAX_RESULTS


def test_position_biases_search(user_client, geocoder):
    user_client.get(URL, {"q": "pho", "latitude": 10.7812, "longitude": 106.7034})

    assert geocoder.calls[0]["lat"] == "10.78"
    assert geocoder.calls[0]["lon"] == "106.70"


def test_repeated_search_uses_cache(user_client, geocoder):
    user_client.get(URL, {"q": "Tan Binh"})
    user_client.get(URL, {"q": "  tan   binh "})

    assert len(geocoder.calls) == 1


def test_no_results_returns_empty_list(user_client, geocoder):
    geocoder.results = []

    response = user_client.get(URL, {"q": "zzzz"})

    assert response.status_code == 200
    assert response.json() == []


def test_upstream_failure_returns_503(user_client, monkeypatch):
    def broken(params):
        raise URLError("down")

    monkeypatch.setattr(services, "_fetch", broken)

    response = user_client.get(URL, {"q": "tan binh"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Place search is unavailable right now."


def test_malformed_upstream_response_returns_503(user_client, geocoder):
    geocoder.results = [{"properties": {"countrycode": "VN"}}]

    assert user_client.get(URL, {"q": "tan binh"}).status_code == 503


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"q": "a"},
        {"q": "x" * 201},
        {"q": "pho", "latitude": 10.78},
        {"q": "pho", "latitude": 100, "longitude": 106.7},
    ],
)
def test_invalid_query_returns_400(user_client, geocoder, params):
    assert user_client.get(URL, params).status_code == 400
    assert geocoder.calls == []


def test_anonymous_cannot_search(anon_client, geocoder):
    assert anon_client.get(URL, {"q": "tan binh"}).status_code == 401


def test_search_is_throttled(user_client, geocoder):
    statuses = [
        user_client.get(URL, {"q": f"place {n}"}).status_code for n in range(31)
    ]

    assert statuses[:30] == [200] * 30
    assert statuses[30] == 429
