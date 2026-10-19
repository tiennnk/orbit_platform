import pytest
from rest_framework.test import APIClient

from apps.drivers.models import Driver
from apps.drivers.services import approve_driver, go_online, register_driver

PASSWORD = "secret-pass-123"


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="driver1", password=PASSWORD)


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(username="driver2", password=PASSWORD)


@pytest.fixture
def driver(user) -> Driver:
    return register_driver(user=user, full_name="Nguyen Van A", phone="0901234567")


@pytest.fixture
def anon_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def other_client(other_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=other_user)
    return client


@pytest.fixture
def staff_client(admin_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def online_driver(driver) -> Driver:
    approve_driver(driver_id=driver.id)
    return go_online(driver_id=driver.id)
