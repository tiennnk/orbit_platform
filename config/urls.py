from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token

from apps.shared.health import HealthView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", HealthView.as_view(), name="health"),
    path("api/v1/auth/token/", obtain_auth_token, name="auth-token"),
    path("api/v1/drivers/", include("apps.drivers.api.urls")),
    path("api/v1/rides/", include("apps.rides.api.urls")),
]
