import unicodedata
from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser

from apps.food.models import FoodOrder, MenuItem
from apps.food.selectors import (
    find_nearby_restaurants,
    get_public_restaurant,
    list_customer_orders,
)
from apps.shared.exceptions import DomainError

SEARCH_RADIUS_KM = 5.0
CANDIDATE_LIMIT = 50
MAX_RESULTS = 8
MAX_ORDERS = 10


class ToolError(Exception):
    pass


@dataclass(frozen=True)
class ToolContext:
    user: AbstractBaseUser
    location: tuple[float, float] | None


TOOLS = [
    {
        "name": "search_restaurants",
        "description": (
            "Find approved restaurants within 5 km of the customer, open ones first, "
            "then by distance. Optionally filter by restaurant name, by dish name, "
            "or by a maximum dish price in VND. Matching ignores Vietnamese accents."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Part of the restaurant name.",
                },
                "dish": {
                    "type": "string",
                    "description": "Part of a dish name, e.g. pho.",
                },
                "max_price": {
                    "type": "integer",
                    "description": "Only dishes at or below this price in VND.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_menu",
        "description": "Get one restaurant's details and full menu by its id.",
        "input_schema": {
            "type": "object",
            "properties": {"restaurant_id": {"type": "integer"}},
            "required": ["restaurant_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_my_orders",
        "description": (
            "List the customer's most recent food orders, newest first, "
            "with status, delivery status, items and totals."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_ORDERS}
            },
            "additionalProperties": False,
        },
    },
]


def _fold(text: str) -> str:
    text = text.lower().replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _dish(item: MenuItem) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "price": item.price,
        "available": item.is_available,
    }


def search_restaurants(
    context: ToolContext,
    *,
    name: str = "",
    dish: str = "",
    max_price: int | None = None,
) -> dict:
    if context.location is None:
        raise ToolError("The customer's location is unknown.")

    latitude, longitude = context.location
    nearby = find_nearby_restaurants(
        latitude=latitude,
        longitude=longitude,
        radius_km=SEARCH_RADIUS_KM,
        limit=CANDIDATE_LIMIT,
    )
    if name:
        wanted = _fold(name)
        nearby = [n for n in nearby if wanted in _fold(n.restaurant.name)]

    filter_dishes = bool(dish) or max_price is not None
    dishes: dict[int, list[MenuItem]] = {}
    if filter_dishes:
        wanted = _fold(dish)
        items = MenuItem.objects.filter(
            restaurant__in=[n.restaurant for n in nearby], is_available=True
        ).order_by("price", "id")
        if max_price is not None:
            items = items.filter(price__lte=max_price)
        for item in items:
            if wanted in _fold(item.name):
                dishes.setdefault(item.restaurant_id, []).append(item)

    results = []
    for n in nearby:
        if filter_dishes and n.restaurant.id not in dishes:
            continue
        entry = {
            "id": n.restaurant.id,
            "name": n.restaurant.name,
            "address": n.restaurant.address,
            "is_open": n.restaurant.is_open,
            "distance_km": round(n.distance_km, 1),
        }
        if filter_dishes:
            entry["matching_dishes"] = [_dish(i) for i in dishes[n.restaurant.id]]
        results.append(entry)
        if len(results) == MAX_RESULTS:
            break
    return {"restaurants": results}


def get_menu(context: ToolContext, *, restaurant_id: int) -> dict:
    restaurant = get_public_restaurant(restaurant_id=restaurant_id)
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "address": restaurant.address,
        "phone": restaurant.phone,
        "is_open": restaurant.is_open,
        "menu": [_dish(item) for item in restaurant.menu_items.all()],
    }


def _order(order: FoodOrder) -> dict:
    return {
        "id": order.id,
        "restaurant": order.restaurant.name,
        "status": order.status,
        "delivery_status": order.delivery.status if order.delivery else None,
        "items": [f"{line.quantity} x {line.name}" for line in order.lines.all()],
        "total": order.total,
        "created_at": order.created_at.isoformat(),
    }


def list_my_orders(context: ToolContext, *, limit: int = 5) -> dict:
    limit = max(1, min(limit, MAX_ORDERS))
    orders = list_customer_orders(user=context.user)[:limit]
    return {"orders": [_order(order) for order in orders]}


HANDLERS = {
    "search_restaurants": search_restaurants,
    "get_menu": get_menu,
    "list_my_orders": list_my_orders,
}


def run_tool(context: ToolContext, name: str, arguments: dict) -> dict:
    handler = HANDLERS.get(name)
    if handler is None:
        raise ToolError(f"Unknown tool {name}.")
    try:
        return handler(context, **arguments)
    except TypeError as exc:
        raise ToolError(f"Invalid arguments for {name}.") from exc
    except DomainError as exc:
        raise ToolError(str(exc)) from exc
