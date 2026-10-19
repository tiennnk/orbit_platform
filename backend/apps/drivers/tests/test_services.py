import pytest

from apps.drivers.domain import Availability, DriverAlreadyExists
from apps.drivers.models import Driver
from apps.drivers.services import register_driver
from apps.shared.domain import ApprovalStatus

pytestmark = pytest.mark.django_db


def test_register_driver_creates_pending_offline_driver(user):
    driver = register_driver(user=user, full_name="Nguyen Van A", phone="0901234567")

    driver.refresh_from_db()
    assert driver.user == user
    assert driver.approval_status == ApprovalStatus.PENDING
    assert driver.is_online is False
    assert driver.availability == Availability.AVAILABLE


def test_register_driver_strips_whitespace(user):
    driver = register_driver(
        user=user, full_name="  Nguyen Van A  ", phone=" 0901234567 "
    )

    assert driver.full_name == "Nguyen Van A"
    assert driver.phone == "0901234567"


def test_register_driver_rejects_duplicate_phone(user, other_user):
    register_driver(user=user, full_name="A", phone="0901234567")

    with pytest.raises(DriverAlreadyExists, match="phone"):
        register_driver(user=other_user, full_name="B", phone="0901234567")


def test_duplicate_phone_with_spaces_is_rejected(user, other_user):
    register_driver(user=user, full_name="A", phone="0901234567")

    with pytest.raises(DriverAlreadyExists, match="phone"):
        register_driver(user=other_user, full_name="B", phone=" 0901234567 ")


def test_same_user_cannot_register_twice(user):
    register_driver(user=user, full_name="A", phone="0901234567")

    with pytest.raises(DriverAlreadyExists, match="account"):
        register_driver(user=user, full_name="A", phone="0907654321")


def test_database_still_usable_after_duplicate_error(user, other_user):
    register_driver(user=user, full_name="A", phone="0901234567")
    with pytest.raises(DriverAlreadyExists):
        register_driver(user=other_user, full_name="B", phone="0901234567")

    register_driver(user=other_user, full_name="C", phone="0907654321")
    assert Driver.objects.count() == 2
