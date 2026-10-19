import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

from apps.shared.exceptions import UnavailableError

MAX_RESULTS = 5
FETCH_LIMIT = 15
CACHE_TTL = timedelta(days=1)
ADDRESS_PARTS = ("locality", "district", "city", "state", "country")
SHORT_ADDRESS_PARTS = ("district", "city")
LOOKUP_ERRORS = (URLError, TimeoutError, ValueError, KeyError, TypeError)


class PlaceSearchUnavailable(UnavailableError):
    pass


@dataclass(frozen=True)
class Place:
    name: str
    address: str
    latitude: float
    longitude: float


def _fetch(url: str, params: dict[str, str]) -> dict:
    request = Request(
        f"{url}?{urlencode(params)}",
        headers={"User-Agent": settings.GEOCODER_USER_AGENT},
    )
    with urlopen(request, timeout=settings.GEOCODER_TIMEOUT) as response:
        return json.load(response)


def _address(props: dict, keys: tuple[str, ...] = ADDRESS_PARTS) -> str:
    street = " ".join(
        part for part in (props.get("housenumber"), props.get("street")) if part
    )
    parts = [street, *(props.get(key) for key in keys)]
    seen = {props.get("name")}
    address = []
    for part in parts:
        if part and part not in seen:
            seen.add(part)
            address.append(part)
    return ", ".join(address)


def _to_place(feature: dict) -> Place:
    props = feature["properties"]
    longitude, latitude = feature["geometry"]["coordinates"]
    address = _address(props)
    return Place(
        name=props.get("name") or address.split(",")[0],
        address=address,
        latitude=float(latitude),
        longitude=float(longitude),
    )


def _allowed_countries() -> set[str]:
    return {
        code.strip().upper()
        for code in settings.GEOCODER_COUNTRY_CODES.split(",")
        if code.strip()
    }


def search_places(
    *, query: str, near: tuple[float, float] | None = None
) -> list[Place]:
    query = " ".join(query.split()).lower()
    params = {"q": query, "limit": str(FETCH_LIMIT)}
    if near is not None:
        params["lat"] = f"{near[0]:.2f}"
        params["lon"] = f"{near[1]:.2f}"

    key = (
        "places:"
        + hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    )
    cached = cache.get(key)
    if cached is not None:
        return cached

    countries = _allowed_countries()
    try:
        features = _fetch(settings.GEOCODER_URL, params)["features"]
        places = list(
            dict.fromkeys(
                _to_place(feature)
                for feature in features
                if not countries
                or feature["properties"].get("countrycode", "").upper() in countries
            )
        )[:MAX_RESULTS]
    except LOOKUP_ERRORS as exc:
        raise PlaceSearchUnavailable("Place search is unavailable right now.") from exc

    cache.set(key, places, CACHE_TTL.total_seconds())
    return places


def reverse_address(*, latitude: float, longitude: float) -> str | None:
    params = {"lat": f"{latitude:.6f}", "lon": f"{longitude:.6f}", "limit": "1"}
    try:
        features = _fetch(settings.GEOCODER_REVERSE_URL, params)["features"]
        if not features:
            return None
        return _address(features[0]["properties"], SHORT_ADDRESS_PARTS) or None
    except LOOKUP_ERRORS as exc:
        raise PlaceSearchUnavailable("Place search is unavailable right now.") from exc
