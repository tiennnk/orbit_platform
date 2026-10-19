from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/token/", obtain_auth_token, name="auth-token"),
    path("api/v1/drivers/", include("apps.drivers.api.urls")),
    path("api/v1/rides/", include("apps.rides.api.urls")),
]
