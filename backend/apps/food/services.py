from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.food.domain import (
    InvalidOrder,
    InvalidOrderTransition,
    MenuItemNameTaken,
    MenuItemNotFound,
    OrderNotFound,
    OrderStatus,
    RestaurantAlreadyExists,
    RestaurantNotAcceptingOrders,
    RestaurantNotFound,
)
from apps.food.models import (
    MENU_ITEM_NAME_CONSTRAINT,
    OWNER_UNIQUE_CONSTRAINT,
    FoodOrder,
    MenuItem,
    OrderLine,
    Restaurant,
)
from apps.rides.domain import RideStatus
from apps.rides.services import advance_dispatch, estimate_trip, request_delivery
from apps.shared.db import violated_constraint
from apps.shared.domain import ApprovalStatus

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


MAX_DELIVERY_KM = 10.0


@dataclass(frozen=True)
class DeliveryQuote:
    distance_km: float
    delivery_fee: int
    deliverable: bool


def quote_delivery(
    *, restaurant: Restaurant, latitude: float, longitude: float
) -> DeliveryQuote:
    distance_km, fee = estimate_trip(
        pickup=(restaurant.latitude, restaurant.longitude),
        dropoff=(latitude, longitude),
    )
    return DeliveryQuote(
        distance_km=distance_km,
        delivery_fee=fee,
        deliverable=distance_km <= MAX_DELIVERY_KM,
    )


def place_order(
    *,
    customer: AbstractBaseUser,
    restaurant_id: int,
    items: list[dict],
    delivery_latitude: float,
    delivery_longitude: float,
    delivery_address: str = "",
    note: str = "",
) -> FoodOrder:
    restaurant = Restaurant.objects.filter(
        pk=restaurant_id, approval_status=ApprovalStatus.APPROVED
    ).first()
    if restaurant is None:
        raise RestaurantNotFound(f"Restaurant {restaurant_id} not found.")
    if not restaurant.is_open:
        raise RestaurantNotAcceptingOrders(f"{restaurant.name} is closed right now.")
    if restaurant.owner_id == customer.pk:
        raise InvalidOrder("You cannot order from your own restaurant.")

    quantities = {item["menu_item_id"]: item["quantity"] for item in items}
    menu = {
        item.id: item
        for item in MenuItem.objects.filter(restaurant=restaurant, pk__in=quantities)
    }
    if len(menu) != len(quantities):
        raise InvalidOrder("Some dishes are not on this restaurant's menu.")
    sold_out = [item.name for item in menu.values() if not item.is_available]
    if sold_out:
        raise InvalidOrder(f"Sold out: {', '.join(sorted(sold_out))}.")

    quote = quote_delivery(
        restaurant=restaurant, latitude=delivery_latitude, longitude=delivery_longitude
    )
    if not quote.deliverable:
        raise InvalidOrder(
            f"{restaurant.name} only delivers within {MAX_DELIVERY_KM:g} km."
        )

    subtotal = sum(menu[pk].price * quantity for pk, quantity in quantities.items())
    with transaction.atomic():
        order = FoodOrder.objects.create(
            customer=customer,
            restaurant=restaurant,
            delivery_latitude=delivery_latitude,
            delivery_longitude=delivery_longitude,
            delivery_address=delivery_address.strip(),
            note=note.strip(),
            subtotal=subtotal,
            delivery_fee=quote.delivery_fee,
            total=subtotal + quote.delivery_fee,
        )
        OrderLine.objects.bulk_create(
            OrderLine(
                order=order,
                menu_item=menu[pk],
                name=menu[pk].name,
                unit_price=menu[pk].price,
                quantity=quantity,
            )
            for pk, quantity in quantities.items()
        )

    return order


def _lock_order(**filters) -> FoodOrder:
    order = (
        FoodOrder.objects.select_for_update(of=("self",))
        .select_related("restaurant")
        .filter(**filters)
        .first()
    )
    if order is None:
        raise OrderNotFound(f"Order {filters.get('pk')} not found.")
    return order


def _dispatch(order: FoodOrder) -> None:
    restaurant = order.restaurant
    order.delivery = request_delivery(
        customer=order.customer,
        pickup=(restaurant.latitude, restaurant.longitude),
        dropoff=(order.delivery_latitude, order.delivery_longitude),
        pickup_label=f"{restaurant.name}, {restaurant.address}".strip(", "),
        dropoff_label=order.delivery_address,
    )


def accept_order(*, restaurant: Restaurant, order_id: int) -> FoodOrder:
    with transaction.atomic():
        order = _lock_order(pk=order_id, restaurant=restaurant)
        order.accept(timezone.now())
        _dispatch(order)
        order.save(update_fields=["status", "accepted_at", "delivery", "updated_at"])

    return refresh_delivery(order)


def reject_order(*, restaurant: Restaurant, order_id: int) -> FoodOrder:
    with transaction.atomic():
        order = _lock_order(pk=order_id, restaurant=restaurant)
        order.reject(timezone.now())
        order.save(update_fields=["status", "closed_at", "updated_at"])

    return order


def cancel_order(*, customer: AbstractBaseUser, order_id: int) -> FoodOrder:
    with transaction.atomic():
        order = _lock_order(pk=order_id, customer=customer)
        order.cancel(timezone.now())
        order.save(update_fields=["status", "closed_at", "updated_at"])

    return order


def redispatch_order(*, restaurant: Restaurant, order_id: int) -> FoodOrder:
    with transaction.atomic():
        order = _lock_order(pk=order_id, restaurant=restaurant)
        if order.status != OrderStatus.ACCEPTED or (
            order.delivery is not None and order.delivery.status != RideStatus.NO_DRIVER
        ):
            raise InvalidOrderTransition(
                "Only orders that found no driver can search again."
            )
        _dispatch(order)
        order.save(update_fields=["delivery", "updated_at"])

    return refresh_delivery(order)


def refresh_delivery(order: FoodOrder) -> FoodOrder:
    if order.delivery is not None and order.delivery.status == RideStatus.SEARCHING:
        order.delivery = advance_dispatch(ride_id=order.delivery_id)
    return order
