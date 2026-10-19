from django.urls import path

from apps.accounts.api.views import (
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("password/", PasswordChangeView.as_view(), name="auth-password"),
]
