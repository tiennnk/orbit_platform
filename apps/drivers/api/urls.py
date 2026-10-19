from django.urls import path

from apps.drivers.api.views import (
    DriverApproveView,
    DriverCreateView,
    DriverDetailView,
)

urlpatterns = [
    path("", DriverCreateView.as_view(), name="driver-create"),
    path("<int:pk>/", DriverDetailView.as_view(), name="driver-detail"),
    path("<int:pk>/approve/", DriverApproveView.as_view(), name="driver-approve"),
]
