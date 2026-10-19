from django.contrib.auth.models import AbstractBaseUser
from django.db import IntegrityError, transaction

from apps.food.domain import (
    MenuItemNameTaken,
    MenuItemNotFound,
    RestaurantAlreadyExists,
    RestaurantNotFound,
)
from apps.food.models import (
    MENU_ITEM_NAME_CONSTRAINT,
    OWNER_UNIQUE_CONSTRAINT,
    MenuItem,
    Restaurant,
)
from apps.shared.db import violated_constraint

PROFILE_FIELDS = ["name", "phone", "address", "latitude", "longitude"]


def _clean(fields: dict) -> dict:
    return {
        key: value.strip() if isinstance(value, str) else value
        for key, value in fields.items()
    }


def register_restaurant(
    *,
    owner: AbstractBaseUser,
    name: str,
    phone: str,
    address: str,
    latitude: float,
    longitude: float,
) -> Restaurant:
    fields = _clean(
        {
            "name": name,
            "phone": phone,
            "address": address,
            "latitude": latitude,
            "longitude": longitude,
        }
    )
    try:
        with transaction.atomic():
            return Restaurant.objects.create(owner=owner, **fields)
    except IntegrityError as exc:
        if violated_constraint(exc) == OWNER_UNIQUE_CONSTRAINT:
            raise RestaurantAlreadyExists(
                "This account already has a restaurant."
            ) from exc
        raise


def _get_restaurant_for_update(restaurant_id: int) -> Restaurant:
    try:
        return Restaurant.objects.select_for_update().get(pk=restaurant_id)
    except Restaurant.DoesNotExist as exc:
        raise RestaurantNotFound(f"Restaurant {restaurant_id} not found.") from exc


def _transition(restaurant_id: int, action: str, fields: list[str]) -> Restaurant:
    with transaction.atomic():
        restaurant = _get_restaurant_for_update(restaurant_id)
        getattr(restaurant, action)()
        restaurant.save(update_fields=[*fields, "updated_at"])

    return restaurant


def approve_restaurant(*, restaurant_id: int) -> Restaurant:
    return _transition(restaurant_id, "approve", ["approval_status"])


def reject_restaurant(*, restaurant_id: int) -> Restaurant:
    return _transition(restaurant_id, "reject", ["approval_status"])


def suspend_restaurant(*, restaurant_id: int) -> Restaurant:
    return _transition(restaurant_id, "suspend", ["approval_status", "is_open"])


def reinstate_restaurant(*, restaurant_id: int) -> Restaurant:
    return _transition(restaurant_id, "reinstate", ["approval_status"])


def open_restaurant(*, restaurant_id: int) -> Restaurant:
    return _transition(restaurant_id, "open", ["is_open"])


def close_restaurant(*, restaurant_id: int) -> Restaurant:
    return _transition(restaurant_id, "close", ["is_open"])


def update_restaurant_profile(
    *,
    restaurant_id: int,
    name: str,
    phone: str,
    address: str,
    latitude: float,
    longitude: float,
) -> Restaurant:
    fields = _clean(
        {
            "name": name,
            "phone": phone,
            "address": address,
            "latitude": latitude,
            "longitude": longitude,
        }
    )
    with transaction.atomic():
        restaurant = _get_restaurant_for_update(restaurant_id)
        restaurant.update_profile(**fields)
        restaurant.save(
            update_fields=[*PROFILE_FIELDS, "approval_status", "updated_at"]
        )

    return restaurant


def _save_menu_item(item: MenuItem, update_fields: list[str] | None = None) -> None:
    try:
        with transaction.atomic():
            item.save(update_fields=update_fields)
    except IntegrityError as exc:
        if violated_constraint(exc) == MENU_ITEM_NAME_CONSTRAINT:
            raise MenuItemNameTaken(
                f"The menu already has an item called {item.name}."
            ) from exc
        raise


def add_menu_item(
    *,
    restaurant: Restaurant,
    name: str,
    price: int,
    description: str = "",
    is_available: bool = True,
) -> MenuItem:
    item = MenuItem(
        restaurant=restaurant,
        name=name.strip(),
        description=description.strip(),
        price=price,
        is_available=is_available,
    )
    _save_menu_item(item)
    return item


def _get_menu_item(restaurant: Restaurant, item_id: int) -> MenuItem:
    try:
        return MenuItem.objects.get(pk=item_id, restaurant=restaurant)
    except MenuItem.DoesNotExist as exc:
        raise MenuItemNotFound(f"Menu item {item_id} not found.") from exc


def update_menu_item(
    *,
    restaurant: Restaurant,
    item_id: int,
    name: str,
    price: int,
    description: str = "",
    is_available: bool = True,
) -> MenuItem:
    item = _get_menu_item(restaurant, item_id)
    item.name = name.strip()
    item.description = description.strip()
    item.price = price
    item.is_available = is_available
    _save_menu_item(
        item, ["name", "description", "price", "is_available", "updated_at"]
    )
    return item


def delete_menu_item(*, restaurant: Restaurant, item_id: int) -> None:
    _get_menu_item(restaurant, item_id).delete()
