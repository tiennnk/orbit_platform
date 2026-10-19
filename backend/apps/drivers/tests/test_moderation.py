import pytest
from django.utils import timezone

from apps.drivers.domain import ApprovalStatus
from apps.drivers.models import DriverLocation
from apps.drivers.services import approve_driver, go_online, register_driver
from apps.rides.services import request_ride

pytestmark = pytest.mark.django_db

URL = "/api/v1/drivers/"
ME_URL = f"{URL}me/"


def test_staff_rejects_pending_driver(driver, staff_client):
    response = staff_client.post(f"{URL}{driver.id}/reject/")

    assert response.status_code == 200
    assert response.json()["approval_status"] == "rejected"


def test_staff_suspends_online_driver(online_driver, staff_client):
    response = staff_client.post(f"{URL}{online_driver.id}/suspend/")

    assert response.status_code == 200
    body = response.json()
    assert body["approval_status"] == "suspended"
    assert body["is_online"] is False


def test_suspended_driver_cannot_go_online(online_driver, staff_client, user_client):
    staff_client.post(f"{URL}{online_driver.id}/suspend/")

    assert user_client.post(f"{ME_URL}online/").status_code == 409


def test_cannot_suspend_driver_during_ride(
    online_driver, staff_client, django_user_model
):
    DriverLocation.objects.create(
        driver=online_driver,
        latitude=10.7769,
        longitude=106.7009,
        recorded_at=timezone.now(),
    )
    rider = django_user_model.objects.create_user(username="rider-mod")
    request_ride(
        rider=rider,
        pickup_latitude=10.7769,
        pickup_longitude=106.7009,
        dropoff_latitude=10.8231,
        dropoff_longitude=106.6297,
    )

    response = staff_client.post(f"{URL}{online_driver.id}/suspend/")

    assert response.status_code == 409
    online_driver.refresh_from_db()
    assert online_driver.approval_status == ApprovalStatus.APPROVED


def test_staff_reinstates_suspended_driver(online_driver, staff_client):
    staff_client.post(f"{URL}{online_driver.id}/suspend/")

    response = staff_client.post(f"{URL}{online_driver.id}/reinstate/")

    assert response.status_code == 200
    assert response.json()["approval_status"] == "approved"
    assert response.json()["is_online"] is False


@pytest.mark.parametrize("action", ["reject", "suspend", "reinstate"])
def test_moderation_is_staff_only(driver, user_client, action):
    assert user_client.post(f"{URL}{driver.id}/{action}/").status_code == 403


@pytest.mark.parametrize("action", ["reject", "suspend", "reinstate"])
def test_moderation_unknown_driver_returns_404(staff_client, action):
    assert staff_client.post(f"{URL}999999/{action}/").status_code == 404


def test_pending_driver_updates_profile(driver, user_client):
    response = user_client.put(
        ME_URL, {"full_name": "  Tran Van B  ", "phone": "0912345678"}, format="json"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Tran Van B"
    assert body["phone"] == "0912345678"


def test_rejected_driver_resubmits_by_updating(driver, user_client, staff_client):
    staff_client.post(f"{URL}{driver.id}/reject/")

    response = user_client.put(
        ME_URL, {"full_name": "Fixed", "phone": "0912345678"}, format="json"
    )

    assert response.json()["approval_status"] == "pending"


def test_approved_driver_cannot_update_profile(driver, user_client):
    approve_driver(driver_id=driver.id)

    response = user_client.put(
        ME_URL, {"full_name": "X", "phone": "0912345678"}, format="json"
    )

    assert response.status_code == 409
    driver.refresh_from_db()
    assert driver.full_name == "Nguyen Van A"


def test_update_to_taken_phone_returns_409(driver, user_client, other_user):
    register_driver(user=other_user, full_name="Other", phone="0999999999")

    response = user_client.put(
        ME_URL, {"full_name": "A", "phone": "0999999999"}, format="json"
    )

    assert response.status_code == 409
    assert "phone" in response.json()["detail"]


def test_update_without_profile_returns_404(user_client):
    response = user_client.put(
        ME_URL, {"full_name": "A", "phone": "0912345678"}, format="json"
    )

    assert response.status_code == 404


def test_go_online_still_works_after_reinstate(online_driver, staff_client):
    staff_client.post(f"{URL}{online_driver.id}/suspend/")
    staff_client.post(f"{URL}{online_driver.id}/reinstate/")

    assert go_online(driver_id=online_driver.id).is_online is True
