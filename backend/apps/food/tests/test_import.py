from urllib.error import HTTPError

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.food import osm
from apps.food.management.commands import import_restaurants
from apps.food.models import MenuItem, Restaurant
from apps.places.services import PlaceSearchUnavailable

pytestmark = pytest.mark.django_db

HAI_LUA = {
    "type": "node",
    "id": 939234266,
    "lat": 10.7807008,
    "lon": 106.7067111,
    "tags": {
        "amenity": "restaurant",
        "name": "Nhà Hàng Hai Lúa Sài Gòn",
        "addr:housenumber": "12",
        "addr:street": "Ngô Văn Năm",
        "addr:city": "Hồ Chí Minh",
        "phone": "+84 28 3823 4567",
    },
}

PHO_WAY = {
    "type": "way",
    "id": 55,
    "center": {"lat": 10.7790, "lon": 106.7010},
    "tags": {"amenity": "restaurant", "name": "Phở Hòa Pasteur"},
}

UNNAMED = {"type": "node", "id": 7, "lat": 10.78, "lon": 106.70, "tags": {}}


@pytest.fixture
def overpass(monkeypatch):
    def fake_fetch(query):
        fake_fetch.queries.append(query)
        return {"elements": fake_fetch.elements}

    fake_fetch.queries = []
    fake_fetch.elements = [HAI_LUA, PHO_WAY, UNNAMED]
    monkeypatch.setattr(osm, "_fetch", fake_fetch)
    return fake_fetch


@pytest.fixture
def reverse(monkeypatch):
    calls = []

    def fake_reverse(*, latitude, longitude):
        calls.append((latitude, longitude))
        return "Pasteur, Sai Gon, Ho Chi Minh"

    monkeypatch.setattr(import_restaurants, "reverse_address", fake_reverse)
    monkeypatch.setattr(import_restaurants, "REVERSE_DELAY_SECONDS", 0)
    return calls


def test_import_creates_restaurants_with_menus(overpass, reverse):
    call_command("import_restaurants")

    hai_lua = Restaurant.objects.get(owner__username="osm_n939234266")
    assert hai_lua.name == "Nhà Hàng Hai Lúa Sài Gòn"
    assert hai_lua.address == "12 Ngô Văn Năm, Hồ Chí Minh"
    assert hai_lua.phone == "+84 28 3823 4567"
    assert hai_lua.approval_status == "approved"
    assert hai_lua.is_open is True
    assert hai_lua.menu_items.count() == len(osm.MENUS["vietnamese"])

    pho = Restaurant.objects.get(owner__username="osm_w55")
    assert pho.address == "Pasteur, Sai Gon, Ho Chi Minh"
    assert pho.phone == ""
    assert set(pho.menu_items.values_list("name", flat=True)) == {
        name for name, _ in osm.MENUS["pho"]
    }
    assert reverse == [(10.7790, 106.7010)]
    assert Restaurant.objects.count() == 2


def test_query_targets_area(overpass, reverse):
    call_command("import_restaurants", latitude=21.03, longitude=105.85, radius_km=2)

    assert "around:2000,21.03,105.85" in overpass.queries[0]


def test_reimport_updates_without_duplicates(overpass, reverse):
    call_command("import_restaurants")
    restaurant = Restaurant.objects.get(owner__username="osm_n939234266")
    restaurant.menu_items.create(name="Owner special", price=99000)
    overpass.elements = [{**HAI_LUA, "tags": {**HAI_LUA["tags"], "name": "Hai Lúa"}}]

    call_command("import_restaurants")

    restaurant.refresh_from_db()
    assert restaurant.name == "Hai Lúa"
    assert Restaurant.objects.count() == 2
    assert restaurant.menu_items.filter(name="Owner special").exists()


def test_limit_keeps_closest(overpass, reverse):
    call_command("import_restaurants", limit=1)

    assert list(Restaurant.objects.values_list("name", flat=True)) == [
        "Phở Hòa Pasteur"
    ]


def test_skip_reverse_leaves_address_blank(overpass, reverse):
    call_command("import_restaurants", skip_reverse=True)

    assert Restaurant.objects.get(owner__username="osm_w55").address == ""
    assert reverse == []


def test_reverse_failure_is_not_fatal(overpass, monkeypatch):
    def broken(**kwargs):
        raise PlaceSearchUnavailable("down")

    monkeypatch.setattr(import_restaurants, "reverse_address", broken)
    monkeypatch.setattr(import_restaurants, "REVERSE_DELAY_SECONDS", 0)

    call_command("import_restaurants")

    assert Restaurant.objects.count() == 2


def test_overpass_failure_raises_command_error(monkeypatch):
    def broken(query):
        raise TimeoutError

    monkeypatch.setattr(osm, "_fetch", broken)

    with pytest.raises(CommandError):
        call_command("import_restaurants")


def test_clear_keeps_real_restaurants(overpass, reverse, make_restaurant):
    real = make_restaurant()
    call_command("import_restaurants")

    call_command("import_restaurants", clear=True)

    assert list(Restaurant.objects.values_list("id", flat=True)) == [real.id]
    assert not MenuItem.objects.exclude(restaurant=real).exists()


@pytest.mark.parametrize(
    ("tags", "kind"),
    [
        ({"name": "Cơm Tấm Ba Ghiền"}, "com_tam"),
        ({"name": "Bánh Mì Huỳnh Hoa"}, "banh_mi"),
        ({"name": "Phở Lệ"}, "pho"),
        ({"name": "Bún Bò Gánh"}, "bun"),
        ({"name": "Burger House"}, "burger"),
        ({"name": "The Coffee House"}, "coffee"),
        ({"name": "Gong Cha", "cuisine": "bubble_tea"}, "tea"),
        ({"name": "Pizza 4P's"}, "pizza"),
        ({"name": "Quán Nhỏ", "cuisine": "japanese;sushi"}, "japanese"),
        ({"name": "Quán Nhỏ", "amenity": "cafe"}, "coffee"),
        ({"name": "Quán Nhỏ", "amenity": "restaurant"}, "vietnamese"),
    ],
)
def test_menu_kind(tags, kind):
    assert osm.menu_kind(tags) == kind


def test_long_phone_is_dropped():
    element = {**HAI_LUA, "tags": {**HAI_LUA["tags"], "phone": "0" * 21}}

    assert osm.parse_element(element).phone == ""


def test_every_menu_is_valid():
    for kind, dishes in osm.MENUS.items():
        names = [name.lower() for name, _ in dishes]
        assert len(names) == len(set(names)), kind
        assert all(0 < price <= 10_000_000 for _, price in dishes), kind


def busy():
    return HTTPError("https://overpass", 502, "Bad Gateway", {}, None)


def test_retries_when_overpass_is_busy(monkeypatch, reverse):
    attempts = []

    def flaky(query):
        attempts.append(query)
        if len(attempts) < 3:
            raise busy()
        return {"elements": [PHO_WAY]}

    monkeypatch.setattr(osm, "_fetch", flaky)
    monkeypatch.setattr(osm.time, "sleep", lambda seconds: None)

    call_command("import_restaurants")

    assert len(attempts) == 3
    assert Restaurant.objects.count() == 1


def test_gives_up_after_retries(monkeypatch):
    def always_busy(query):
        raise busy()

    monkeypatch.setattr(osm, "_fetch", always_busy)
    monkeypatch.setattr(osm.time, "sleep", lambda seconds: None)

    with pytest.raises(CommandError):
        call_command("import_restaurants")


def test_does_not_retry_bad_request(monkeypatch):
    attempts = []

    def bad(query):
        attempts.append(query)
        raise HTTPError("https://overpass", 400, "Bad Request", {}, None)

    monkeypatch.setattr(osm, "_fetch", bad)

    with pytest.raises(CommandError):
        call_command("import_restaurants")
    assert len(attempts) == 1
