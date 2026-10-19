from itertools import count

import pytest

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
