from django.urls import path

from apps.rides.api.views import (
    CurrentOfferView,
    CurrentRideView,
    OfferAcceptView,
    OfferDeclineView,
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
    path("offers/current/", CurrentOfferView.as_view(), name="offer-current"),
    path("offers/<int:pk>/accept/", OfferAcceptView.as_view(), name="offer-accept"),
    path("offers/<int:pk>/decline/", OfferDeclineView.as_view(), name="offer-decline"),
    path("<int:pk>/", RideDetailView.as_view(), name="ride-detail"),
    path("<int:pk>/start/", RideStartView.as_view(), name="ride-start"),
    path("<int:pk>/complete/", RideCompleteView.as_view(), name="ride-complete"),
    path("<int:pk>/cancel/", RideCancelView.as_view(), name="ride-cancel"),
]
