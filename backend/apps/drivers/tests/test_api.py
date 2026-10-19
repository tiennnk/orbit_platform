import pytest

from apps.drivers.domain import ApprovalStatus
from apps.drivers.models import Driver
from apps.drivers.services import approve_driver
from conftest import PASSWORD

pytestmark = pytest.mark.django_db

URL = "/api/v1/drivers/"
ME_URL = f"{URL}me/"
TOKEN_URL = "/api/v1/auth/token/"


def test_anonymous_request_returns_401(anon_client):
    response = anon_client.post(URL, {"full_name": "A", "phone": "0901"}, format="json")

    assert response.status_code == 401


def test_login_with_token_then_register(anon_client, user):
    token_response = anon_client.post(
        TOKEN_URL, {"username": user.username, "password": PASSWORD}, format="json"
    )
    assert token_response.status_code == 200
    token = token_response.json()["token"]

    anon_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    response = anon_client.post(
        URL, {"full_name": "Nguyen Van A", "phone": "0901234567"}, format="json"
    )

    assert response.status_code == 201


def test_wrong_password_gets_no_token(anon_client, user):
    response = anon_client.post(
        TOKEN_URL, {"username": user.username, "password": "wrong"}, format="json"
    )

    assert response.status_code == 400
    assert "token" not in response.json()


def test_register_creates_profile_for_current_user(user_client, user):
    response = user_client.post(
        URL, {"full_name": "Nguyen Van A", "phone": "0901234567"}, format="json"
    )

    assert response.status_code == 201
    body = response.json()
    assert body["approval_status"] == "pending"
    assert body["is_online"] is False
    assert Driver.objects.get(pk=body["id"]).user == user


def test_missing_phone_returns_400(user_client):
    response = user_client.post(URL, {"full_name": "A"}, format="json")

    assert response.status_code == 400
    assert "phone" in response.json()


def test_blank_full_name_returns_400(user_client):
    response = user_client.post(
        URL, {"full_name": "   ", "phone": "0901234567"}, format="json"
    )

    assert response.status_code == 400
    assert "full_name" in response.json()


def test_duplicate_phone_returns_409(driver, other_client):
    response = other_client.post(
        URL, {"full_name": "B", "phone": driver.phone}, format="json"
    )

    assert response.status_code == 409
    assert "phone" in response.json()["detail"]


def test_second_profile_for_same_user_returns_409(driver, user_client):
    response = user_client.post(
        URL, {"full_name": "A", "phone": "0907654321"}, format="json"
    )

    assert response.status_code == 409
    assert "account" in response.json()["detail"]


def test_client_cannot_set_approval_status(user_client):
    response = user_client.post(
        URL,
        {"full_name": "A", "phone": "0901234567", "approval_status": "approved"},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["approval_status"] == "pending"


def test_get_my_driver_profile(driver, user_client):
    response = user_client.get(ME_URL)

    assert response.status_code == 200
    assert response.json()["id"] == driver.id


def test_get_me_without_profile_returns_404(user_client):
    response = user_client.get(ME_URL)

    assert response.status_code == 404
    assert response.json()["detail"] == "This account has no driver profile."


def test_staff_gets_driver_by_id(driver, staff_client):
    response = staff_client.get(f"{URL}{driver.id}/")

    assert response.status_code == 200
    assert response.json()["phone"] == driver.phone


def test_non_staff_cannot_get_driver_by_id(driver, other_client):
    assert other_client.get(f"{URL}{driver.id}/").status_code == 403


def test_get_unknown_driver_returns_404(staff_client):
    response = staff_client.get(f"{URL}999999/")

    assert response.status_code == 404
    assert response.json()["detail"] == "Driver 999999 not found."


def test_staff_approves_pending_driver(driver, staff_client):
    response = staff_client.post(f"{URL}{driver.id}/approve/")

    assert response.status_code == 200
    assert response.json()["approval_status"] == "approved"
    driver.refresh_from_db()
    assert driver.approval_status == ApprovalStatus.APPROVED


def test_approve_twice_returns_409(driver, staff_client):
    staff_client.post(f"{URL}{driver.id}/approve/")

    response = staff_client.post(f"{URL}{driver.id}/approve/")

    assert response.status_code == 409


def test_approve_unknown_driver_returns_404(staff_client):
    response = staff_client.post(f"{URL}999999/approve/")

    assert response.status_code == 404
    assert response.json()["detail"] == "Driver 999999 not found."


def test_driver_cannot_approve_themselves(driver, user_client):
    response = user_client.post(f"{URL}{driver.id}/approve/")

    assert response.status_code == 403
    driver.refresh_from_db()
    assert driver.approval_status == ApprovalStatus.PENDING


def test_pending_driver_cannot_go_online_returns_409(driver, user_client):
    response = user_client.post(f"{ME_URL}online/")

    assert response.status_code == 409


def test_approved_driver_goes_online(driver, user_client):
    approve_driver(driver_id=driver.id)

    response = user_client.post(f"{ME_URL}online/")

    assert response.status_code == 200
    assert response.json()["is_online"] is True
    driver.refresh_from_db()
    assert driver.is_online is True


def test_online_driver_goes_offline(driver, user_client):
    approve_driver(driver_id=driver.id)
    user_client.post(f"{ME_URL}online/")

    response = user_client.post(f"{ME_URL}offline/")

    assert response.status_code == 200
    assert response.json()["is_online"] is False


def test_go_online_without_profile_returns_404(user_client):
    response = user_client.post(f"{ME_URL}online/")

    assert response.status_code == 404
    assert response.json()["detail"] == "This account has no driver profile."


def test_other_user_going_online_does_not_affect_my_driver(driver, other_client):
    approve_driver(driver_id=driver.id)

    other_client.post(f"{ME_URL}online/")

    driver.refresh_from_db()
    assert driver.is_online is False
