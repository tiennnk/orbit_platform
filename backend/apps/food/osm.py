import json
import re
import time
import unicodedata
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

from apps.shared.geo import haversine_km

AMENITIES = ("restaurant", "cafe", "fast_food")
MAX_PHONE_LENGTH = 20
FETCH_TIMEOUT = 120
RETRY_DELAYS = (5, 15, 45)
RETRY_STATUSES = {429, 502, 503, 504}

MENUS: dict[str, list[tuple[str, int]]] = {
    "pho": [("Phở bò tái", 55000), ("Phở bò chín", 55000), ("Phở gà", 50000)],
    "com_tam": [
        ("Cơm tấm sườn", 45000),
        ("Cơm tấm sườn bì chả", 55000),
        ("Cơm gà xối mỡ", 50000),
    ],
    "banh_mi": [
        ("Bánh mì thịt", 25000),
        ("Bánh mì ốp la", 30000),
        ("Bánh mì xíu mại", 30000),
    ],
    "bun": [
        ("Bún bò Huế", 55000),
        ("Bún chả Hà Nội", 50000),
        ("Bún thịt nướng", 45000),
    ],
    "coffee": [
        ("Cà phê sữa đá", 29000),
        ("Bạc xỉu", 32000),
        ("Cà phê đen", 25000),
        ("Trà đào cam sả", 45000),
    ],
    "tea": [
        ("Trà sữa trân châu", 35000),
        ("Trà sữa matcha", 40000),
        ("Trà đào", 39000),
    ],
    "pizza": [
        ("Pizza Margherita", 159000),
        ("Pizza hải sản", 199000),
        ("Mì Ý sốt bò bằm", 129000),
    ],
    "burger": [("Burger bò", 79000), ("Burger gà", 69000), ("Khoai tây chiên", 35000)],
    "chicken": [
        ("Gà rán 2 miếng", 69000),
        ("Cánh gà chiên nước mắm", 79000),
        ("Cơm gà", 49000),
    ],
    "japanese": [("Sushi cá hồi", 120000), ("Ramen", 115000), ("Cơm cà ri", 95000)],
    "korean": [("Cơm trộn", 89000), ("Tokbokki", 69000), ("Gà rán Hàn Quốc", 129000)],
    "seafood": [
        ("Tôm nướng muối ớt", 180000),
        ("Nghêu hấp sả", 90000),
        ("Lẩu hải sản", 350000),
    ],
    "western": [("Bò bít tết", 250000), ("Mì Ý carbonara", 150000), ("Salad", 90000)],
    "vietnamese": [
        ("Cơm chiên dương châu", 60000),
        ("Gỏi cuốn", 40000),
        ("Canh chua cá", 85000),
        ("Rau muống xào tỏi", 50000),
    ],
}

NAME_KEYWORDS = [
    ("com tam", "com_tam"),
    ("banh mi", "banh_mi"),
    ("pho", "pho"),
    ("bun", "bun"),
    ("ca phe", "coffee"),
    ("coffee", "coffee"),
    ("cafe", "coffee"),
    ("tra sua", "tea"),
    ("milk tea", "tea"),
    ("pizza", "pizza"),
    ("burger", "burger"),
    ("ga ran", "chicken"),
    ("chicken", "chicken"),
    ("kfc", "chicken"),
    ("jollibee", "chicken"),
    ("sushi", "japanese"),
    ("ramen", "japanese"),
    ("korea", "korean"),
    ("bbq", "korean"),
    ("hai san", "seafood"),
    ("seafood", "seafood"),
]

CUISINE_KINDS = {
    "pho": "pho",
    "noodle": "bun",
    "coffee_shop": "coffee",
    "coffee": "coffee",
    "bubble_tea": "tea",
    "tea": "tea",
    "pizza": "pizza",
    "burger": "burger",
    "chicken": "chicken",
    "fried_chicken": "chicken",
    "japanese": "japanese",
    "sushi": "japanese",
    "ramen": "japanese",
    "korean": "korean",
    "seafood": "seafood",
    "italian": "western",
    "american": "western",
    "french": "western",
    "steak_house": "western",
    "vietnamese": "vietnamese",
}


@dataclass(frozen=True)
class OsmRestaurant:
    key: str
    name: str
    latitude: float
    longitude: float
    phone: str
    address: str | None
    kind: str


def _plain(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def menu_kind(tags: dict[str, str]) -> str:
    name = f" {re.sub(r'[^a-z0-9]+', ' ', _plain(tags.get('name', '')))} "
    for keyword, kind in NAME_KEYWORDS:
        if f" {keyword} " in name:
            return kind

    for cuisine in tags.get("cuisine", "").split(";"):
        kind = CUISINE_KINDS.get(cuisine.strip().lower())
        if kind:
            return kind

    return "coffee" if tags.get("amenity") == "cafe" else "vietnamese"


def _phone(tags: dict[str, str]) -> str:
    raw = tags.get("phone") or tags.get("contact:phone") or ""
    phone = raw.split(";")[0].strip()
    return phone if len(phone) <= MAX_PHONE_LENGTH else ""


def _address(tags: dict[str, str]) -> str | None:
    if tags.get("addr:full"):
        return tags["addr:full"]
    street = " ".join(
        part for part in (tags.get("addr:housenumber"), tags.get("addr:street")) if part
    )
    if not tags.get("addr:street"):
        return None
    rest = [tags.get(key) for key in ("addr:district", "addr:city")]
    return ", ".join(part for part in [street, *rest] if part)


def parse_element(element: dict) -> OsmRestaurant | None:
    tags = element.get("tags", {})
    name = tags.get("name", "").strip()
    point = element.get("center", element)
    if not name or "lat" not in point or "lon" not in point:
        return None
    return OsmRestaurant(
        key=f"{element['type'][0]}{element['id']}",
        name=name[:120],
        latitude=float(point["lat"]),
        longitude=float(point["lon"]),
        phone=_phone(tags),
        address=_address(tags),
        kind=menu_kind(tags),
    )


def _fetch(query: str) -> dict:
    request = Request(
        settings.OVERPASS_URL,
        data=urlencode({"data": query}).encode(),
        headers={"User-Agent": settings.GEOCODER_USER_AGENT},
    )
    with urlopen(request, timeout=FETCH_TIMEOUT) as response:
        return json.load(response)


def _fetch_with_retry(query: str) -> dict:
    for delay in RETRY_DELAYS:
        try:
            return _fetch(query)
        except HTTPError as exc:
            if exc.code not in RETRY_STATUSES:
                raise
            time.sleep(delay)
    return _fetch(query)


def fetch_restaurants(
    *, latitude: float, longitude: float, radius_km: float, limit: int
) -> list[OsmRestaurant]:
    amenities = "|".join(AMENITIES)
    query = (
        f"[out:json][timeout:{FETCH_TIMEOUT}];"
        f'nwr["amenity"~"^({amenities})$"]["name"]'
        f"(around:{int(radius_km * 1000)},{latitude},{longitude});"
        "out center tags;"
    )
    places = {
        place.key: place
        for element in _fetch_with_retry(query).get("elements", [])
        if (place := parse_element(element))
    }
    return sorted(
        places.values(),
        key=lambda p: haversine_km(latitude, longitude, p.latitude, p.longitude),
    )[:limit]
