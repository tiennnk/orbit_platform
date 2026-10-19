from django.urls import path

from apps.drivers.api.views import (
    DriverApproveView,
    DriverDetailView,
    DriverListCreateView,
    DriverReinstateView,
    DriverRejectView,
    DriverSuspendView,
    MyDriverGoOfflineView,
    MyDriverGoOnlineView,
    MyDriverLocationView,
    MyDriverView,
    NearbyDriversView,
)

urlpatterns = [
    path("", DriverListCreateView.as_view(), name="driver-list-create"),
    path("me/", MyDriverView.as_view(), name="driver-me"),
    path("me/online/", MyDriverGoOnlineView.as_view(), name="driver-me-online"),
    path("me/offline/", MyDriverGoOfflineView.as_view(), name="driver-me-offline"),
    path("me/location/", MyDriverLocationView.as_view(), name="driver-me-location"),
    path("nearby/", NearbyDriversView.as_view(), name="driver-nearby"),
    path("<int:pk>/", DriverDetailView.as_view(), name="driver-detail"),
    path("<int:pk>/approve/", DriverApproveView.as_view(), name="driver-approve"),
    path("<int:pk>/reject/", DriverRejectView.as_view(), name="driver-reject"),
    path("<int:pk>/suspend/", DriverSuspendView.as_view(), name="driver-suspend"),
    path("<int:pk>/reinstate/", DriverReinstateView.as_view(), name="driver-reinstate"),
]
