from django.urls import path

from apps.drivers.api.views import (
    DriverApproveView,
    DriverCreateView,
    DriverDetailView,
    MyDriverGoOfflineView,
    MyDriverGoOnlineView,
    MyDriverLocationView,
    MyDriverView,
)

urlpatterns = [
    path("", DriverCreateView.as_view(), name="driver-create"),
    path("me/", MyDriverView.as_view(), name="driver-me"),
    path("me/online/", MyDriverGoOnlineView.as_view(), name="driver-me-online"),
    path("me/offline/", MyDriverGoOfflineView.as_view(), name="driver-me-offline"),
    path("me/location/", MyDriverLocationView.as_view(), name="driver-me-location"),
    path("<int:pk>/", DriverDetailView.as_view(), name="driver-detail"),
    path("<int:pk>/approve/", DriverApproveView.as_view(), name="driver-approve"),
]
