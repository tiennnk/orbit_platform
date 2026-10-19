from django.urls import path

from apps.food.api.views import (
    MyMenuItemView,
    MyMenuView,
    MyRestaurantCloseView,
    MyRestaurantOpenView,
    MyRestaurantView,
    NearbyRestaurantsView,
    RestaurantApproveView,
    RestaurantDetailView,
    RestaurantListCreateView,
    RestaurantReinstateView,
    RestaurantRejectView,
    RestaurantSuspendView,
)

urlpatterns = [
    path("restaurants/", RestaurantListCreateView.as_view(), name="restaurant-list"),
    path("restaurants/me/", MyRestaurantView.as_view(), name="restaurant-me"),
    path(
        "restaurants/me/open/",
        MyRestaurantOpenView.as_view(),
        name="restaurant-me-open",
    ),
    path(
        "restaurants/me/close/",
        MyRestaurantCloseView.as_view(),
        name="restaurant-me-close",
    ),
    path("restaurants/me/menu/", MyMenuView.as_view(), name="restaurant-me-menu"),
    path(
        "restaurants/me/menu/<int:pk>/",
        MyMenuItemView.as_view(),
        name="restaurant-me-menu-item",
    ),
    path(
        "restaurants/nearby/",
        NearbyRestaurantsView.as_view(),
        name="restaurant-nearby",
    ),
    path(
        "restaurants/<int:pk>/",
        RestaurantDetailView.as_view(),
        name="restaurant-detail",
    ),
    path(
        "restaurants/<int:pk>/approve/",
        RestaurantApproveView.as_view(),
        name="restaurant-approve",
    ),
    path(
        "restaurants/<int:pk>/reject/",
        RestaurantRejectView.as_view(),
        name="restaurant-reject",
    ),
    path(
        "restaurants/<int:pk>/suspend/",
        RestaurantSuspendView.as_view(),
        name="restaurant-suspend",
    ),
    path(
        "restaurants/<int:pk>/reinstate/",
        RestaurantReinstateView.as_view(),
        name="restaurant-reinstate",
    ),
]
