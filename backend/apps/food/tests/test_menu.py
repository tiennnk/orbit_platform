import pytest
from django.db import IntegrityError, transaction

from apps.food.models import MenuItem

pytestmark = pytest.mark.django_db

URL = "/api/v1/food/restaurants/me/menu/"


@pytest.fixture
def restaurant(owner, make_restaurant):
    return make_restaurant(owner=owner)


def test_add_menu_item(owner_client, restaurant):
    response = owner_client.post(
        URL,
        {"name": " Com suon ", "price": 45000, "description": "With egg"},
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Com suon"
    assert body["is_available"] is True
    assert restaurant.menu_items.count() == 1


def test_add_requires_restaurant(owner_client):
    response = owner_client.post(URL, {"name": "Pho", "price": 50000}, format="json")

    assert response.status_code == 404


def test_duplicate_name_is_case_insensitive(owner_client, restaurant):
    owner_client.post(URL, {"name": "Com suon", "price": 45000}, format="json")

    response = owner_client.post(
        URL, {"name": "COM SUON", "price": 50000}, format="json"
    )

    assert response.status_code == 409


def test_same_name_allowed_in_other_restaurants(
    owner_client, restaurant, make_restaurant
):
    make_restaurant().menu_items.create(name="Com suon", price=40000)

    response = owner_client.post(
        URL, {"name": "Com suon", "price": 45000}, format="json"
    )

    assert response.status_code == 201


@pytest.mark.parametrize("price", [0, -1, 10_000_001, "cheap"])
def test_rejects_bad_price(owner_client, restaurant, price):
    response = owner_client.post(URL, {"name": "Pho", "price": price}, format="json")

    assert response.status_code == 400
    assert "price" in response.json()


def test_update_menu_item(owner_client, restaurant):
    item = restaurant.menu_items.create(name="Pho", price=50000)

    response = owner_client.put(
        f"{URL}{item.id}/",
        {"name": "Pho bo", "price": 55000, "is_available": False},
        format="json",
    )

    assert response.status_code == 200
    item.refresh_from_db()
    assert (item.name, item.price, item.is_available) == ("Pho bo", 55000, False)


def test_rename_into_existing_name_returns_409(owner_client, restaurant):
    restaurant.menu_items.create(name="Pho", price=50000)
    item = restaurant.menu_items.create(name="Bun", price=40000)

    response = owner_client.put(
        f"{URL}{item.id}/", {"name": "pho", "price": 40000}, format="json"
    )

    assert response.status_code == 409


def test_delete_menu_item(owner_client, restaurant):
    item = restaurant.menu_items.create(name="Pho", price=50000)

    assert owner_client.delete(f"{URL}{item.id}/").status_code == 204
    assert not MenuItem.objects.filter(pk=item.id).exists()


def test_cannot_touch_other_restaurants_items(
    owner_client, restaurant, make_restaurant
):
    other = make_restaurant().menu_items.create(name="Pho", price=50000)

    assert owner_client.delete(f"{URL}{other.id}/").status_code == 404
    assert (
        owner_client.put(
            f"{URL}{other.id}/", {"name": "Mine", "price": 1}, format="json"
        ).status_code
        == 404
    )
    assert MenuItem.objects.filter(pk=other.id, name="Pho").exists()


def test_public_menu_is_sorted_and_flags_unavailable(owner_client, restaurant):
    restaurant.menu_items.create(name="banh mi", price=25000)
    restaurant.menu_items.create(name="Bun cha", price=50000, is_available=False)

    body = owner_client.get(f"/api/v1/food/restaurants/{restaurant.id}/").json()

    assert [(i["name"], i["is_available"]) for i in body["menu"]] == [
        ("banh mi", True),
        ("Bun cha", False),
    ]


def test_db_rejects_zero_price(restaurant):
    with pytest.raises(IntegrityError), transaction.atomic():
        MenuItem.objects.create(restaurant=restaurant, name="Free", price=0)
