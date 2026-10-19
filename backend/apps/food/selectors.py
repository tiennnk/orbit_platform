import heapq
from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser
from django.db.models import Prefetch, QuerySet
from django.db.models.functions import Lower

from apps.food.domain import RestaurantNotFound
from apps.food.models import MenuItem, Restaurant
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
