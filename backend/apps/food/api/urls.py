from django.urls import path

from apps.food.api.views import (
    DeliveryQuoteView,
    MyMenuItemView,
    MyMenuView,
    MyRestaurantCloseView,
    MyRestaurantOpenView,
    MyRestaurantOrdersView,
    MyRestaurantView,
    NearbyRestaurantsView,
    OrderAcceptView,
    OrderCancelView,
    OrderDetailView,
    OrderListCreateView,
    OrderRedispatchView,
    OrderRejectView,
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
        "restaurants/me/orders/",
        MyRestaurantOrdersView.as_view(),
        name="restaurant-me-orders",
    ),
    path(
        "restaurants/me/orders/<int:pk>/accept/",
        OrderAcceptView.as_view(),
        name="order-accept",
    ),
    path(
        "restaurants/me/orders/<int:pk>/reject/",
        OrderRejectView.as_view(),
        name="order-reject",
    ),
    path(
        "restaurants/me/orders/<int:pk>/redispatch/",
        OrderRedispatchView.as_view(),
        name="order-redispatch",
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
        "restaurants/<int:pk>/delivery-quote/",
        DeliveryQuoteView.as_view(),
        name="restaurant-delivery-quote",
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
    path("orders/", OrderListCreateView.as_view(), name="order-list"),
    path("orders/<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("orders/<int:pk>/cancel/", OrderCancelView.as_view(), name="order-cancel"),
]
