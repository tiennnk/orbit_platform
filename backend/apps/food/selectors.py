import heapq
from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser
from django.db.models import Prefetch, Q, QuerySet
from django.db.models.functions import Lower

from apps.food.domain import OrderNotFound, OrderStatus, RestaurantNotFound
from apps.food.models import FoodOrder, MenuItem, OrderLine, Restaurant
from apps.rides.domain import RideStatus
from apps.shared.domain import ApprovalStatus
from apps.shared.geo import bounding_box, haversine_km


@dataclass(frozen=True)
class NearbyRestaurant:
    restaurant: Restaurant
    distance_km: float


def _menu_prefetch() -> Prefetch:
    return Prefetch(
        "menu_items", queryset=MenuItem.objects.order_by(Lower("name"), "id")
    )


def list_restaurants(*, approval_status: str | None = None) -> QuerySet[Restaurant]:
    restaurants = Restaurant.objects.order_by("created_at", "id")
    if approval_status:
        restaurants = restaurants.filter(approval_status=approval_status)
    return restaurants


def get_restaurant_for_owner(*, user: AbstractBaseUser) -> Restaurant:
    restaurant = (
        Restaurant.objects.prefetch_related(_menu_prefetch()).filter(owner=user).first()
    )
    if restaurant is None:
        raise RestaurantNotFound("This account has no restaurant.")
    return restaurant


def get_restaurant_by_id(*, restaurant_id: int) -> Restaurant:
    try:
        return Restaurant.objects.get(pk=restaurant_id)
    except Restaurant.DoesNotExist as exc:
        raise RestaurantNotFound(f"Restaurant {restaurant_id} not found.") from exc


def get_public_restaurant(*, restaurant_id: int) -> Restaurant:
    restaurant = (
        Restaurant.objects.prefetch_related(_menu_prefetch())
        .filter(pk=restaurant_id, approval_status=ApprovalStatus.APPROVED)
        .first()
    )
    if restaurant is None:
        raise RestaurantNotFound(f"Restaurant {restaurant_id} not found.")
    return restaurant


def find_nearby_restaurants(
    *,
    latitude: float,
    longitude: float,
    radius_km: float,
    limit: int,
    query: str = "",
) -> list[NearbyRestaurant]:
    box = bounding_box(latitude, longitude, radius_km)
    candidates = Restaurant.objects.filter(
        approval_status=ApprovalStatus.APPROVED,
        latitude__range=(box.min_lat, box.max_lat),
        longitude__range=(box.min_lng, box.max_lng),
    )
    if query:
        candidates = candidates.filter(name__icontains=query)

    within_radius = (
        NearbyRestaurant(restaurant=restaurant, distance_km=distance)
        for restaurant in candidates
        if (
            distance := haversine_km(
                latitude, longitude, restaurant.latitude, restaurant.longitude
            )
        )
        <= radius_km
    )
    return heapq.nsmallest(
        limit,
        within_radius,
        key=lambda n: (not n.restaurant.is_open, n.distance_km, n.restaurant.id),
    )


ACTIVE_DELIVERY_STATUSES = (
    RideStatus.SEARCHING,
    RideStatus.ASSIGNED,
    RideStatus.IN_PROGRESS,
    RideStatus.NO_DRIVER,
)


def _orders() -> QuerySet[FoodOrder]:
    return (
        FoodOrder.objects.select_related("restaurant", "delivery__driver")
        .prefetch_related(Prefetch("lines", queryset=OrderLine.objects.order_by("id")))
        .order_by("-created_at", "-id")
    )


def _open_orders() -> Q:
    return Q(status=OrderStatus.PLACED) | Q(
        status=OrderStatus.ACCEPTED, delivery__status__in=ACTIVE_DELIVERY_STATUSES
    )


def list_customer_orders(*, user: AbstractBaseUser) -> QuerySet[FoodOrder]:
    return _orders().filter(customer=user)


def list_restaurant_orders(
    *, restaurant: Restaurant, active: bool
) -> QuerySet[FoodOrder]:
    orders = _orders().filter(restaurant=restaurant)
    return orders.filter(_open_orders()) if active else orders.exclude(_open_orders())


def get_order_for_participant(*, order_id: int, user: AbstractBaseUser) -> FoodOrder:
    order = (
        _orders()
        .filter(Q(customer=user) | Q(restaurant__owner=user), pk=order_id)
        .first()
    )
    if order is None:
        raise OrderNotFound(f"Order {order_id} not found.")
    return order
