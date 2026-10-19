from itertools import count

import pytest
from django.utils import timezone

from apps.drivers.models import Driver, DriverLocation
from apps.food.models import Restaurant
from apps.shared.domain import ApprovalStatus
from conftest import _client_for

CENTER = (10.7769, 106.7009)
KM_IN_LAT_DEGREES = 1 / 111.19

_sequence = count()


@pytest.fixture
def owner(django_user_model):
    return django_user_model.objects.create_user(username="owner1")


@pytest.fixture
def owner_client(owner):
    return _client_for(owner)


@pytest.fixture
def profile():
    return {
        "name": "Com Tam Ba Ghien",
        "phone": "0281234567",
        "address": "84 Dang Van Ngu, Phu Nhuan",
        "latitude": CENTER[0],
        "longitude": CENTER[1],
    }


@pytest.fixture
def make_restaurant(django_user_model):
    def _make(
        km_north: float = 0.5,
        *,
        name: str | None = None,
        status: str = ApprovalStatus.APPROVED,
        is_open: bool = True,
        owner=None,
    ) -> Restaurant:
        n = next(_sequence)
        if owner is None:
            owner = django_user_model.objects.create_user(username=f"resto{n}")
        return Restaurant.objects.create(
            owner=owner,
            name=name or f"Restaurant {n}",
            phone=f"028{n:07d}",
            address=f"{n} Le Loi",
            latitude=CENTER[0] + km_north * KM_IN_LAT_DEGREES,
            longitude=CENTER[1],
            approval_status=status,
            is_open=is_open and status == ApprovalStatus.APPROVED,
        )

    return _make


@pytest.fixture
def customer(django_user_model):
    return django_user_model.objects.create_user(username="customer1")


@pytest.fixture
def customer_client(customer):
    return _client_for(customer)


@pytest.fixture
def make_courier(django_user_model):
    def _make(km_north: float = 0.3) -> Driver:
        n = next(_sequence)
        user = django_user_model.objects.create_user(username=f"courier{n}")
        driver = Driver.objects.create(
            user=user,
            full_name=f"Courier {n}",
            phone=f"07{n:08d}",
            approval_status=ApprovalStatus.APPROVED,
            is_online=True,
        )
        DriverLocation.objects.create(
            driver=driver,
            latitude=CENTER[0] + km_north * KM_IN_LAT_DEGREES,
            longitude=CENTER[1],
            recorded_at=timezone.now(),
        )
        return driver

    return _make


@pytest.fixture
def shop(owner, make_restaurant):
    restaurant = make_restaurant(owner=owner, km_north=0)
    restaurant.menu_items.create(name="Com suon", price=45000)
    restaurant.menu_items.create(name="Tra da", price=5000)
    return restaurant


@pytest.fixture
def order_payload(shop):
    rice, tea = shop.menu_items.order_by("name")
    return {
        "restaurant_id": shop.id,
        "items": [
            {"menu_item_id": rice.id, "quantity": 2},
            {"menu_item_id": tea.id, "quantity": 1},
        ],
        "delivery_latitude": CENTER[0] + 2 * KM_IN_LAT_DEGREES,
        "delivery_longitude": CENTER[1],
        "delivery_address": "12 Nguyen Hue",
        "note": "No chili",
    }
