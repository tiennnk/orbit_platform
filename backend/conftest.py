import pytest
from rest_framework.test import APIClient

PASSWORD = "secret-pass-123"


@pytest.fixture(autouse=True)
def fast_password_hasher(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


def _client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="driver1", password=PASSWORD)


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(username="driver2", password=PASSWORD)


@pytest.fixture
def anon_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user_client(user) -> APIClient:
    return _client_for(user)


@pytest.fixture
def other_client(other_user) -> APIClient:
    return _client_for(other_user)


@pytest.fixture
def staff_client(admin_user) -> APIClient:
    return _client_for(admin_user)
