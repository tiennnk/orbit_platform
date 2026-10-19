from django.urls import path

from apps.rides.api.views import (
    CurrentRideView,
    RideCancelView,
    RideCompleteView,
    RideDetailView,
    RideHistoryView,
    RideRequestView,
    RideStartView,
)

urlpatterns = [
    path("", RideRequestView.as_view(), name="ride-request"),
    path("current/", CurrentRideView.as_view(), name="ride-current"),
    path("history/", RideHistoryView.as_view(), name="ride-history"),
    path("<int:pk>/", RideDetailView.as_view(), name="ride-detail"),
    path("<int:pk>/start/", RideStartView.as_view(), name="ride-start"),
    path("<int:pk>/complete/", RideCompleteView.as_view(), name="ride-complete"),
    path("<int:pk>/cancel/", RideCancelView.as_view(), name="ride-cancel"),
]
