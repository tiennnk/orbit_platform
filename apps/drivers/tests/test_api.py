import pytest
from rest_framework.test import APIClient

from apps.drivers.domain import ApprovalStatus
from apps.drivers.models import Driver
from apps.drivers.services import register_driver

pytestmark = pytest.mark.django_db

URL = "/api/v1/drivers/"


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_create_driver_returns_201(api_client):
    response = api_client.post(
        URL, {"full_name": "Nguyen Van A", "phone": "0901234567"}, format="json"
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == Driver.objects.get().id
    assert body["full_name"] == "Nguyen Van A"
    assert body["approval_status"] == "pending"
    assert body["is_online"] is False
    assert body["availability"] == "available"


def test_missing_phone_returns_400(api_client):
    response = api_client.post(URL, {"full_name": "A"}, format="json")

    assert response.status_code == 400
    assert "phone" in response.json()
    assert Driver.objects.count() == 0


def test_blank_full_name_returns_400(api_client):
    response = api_client.post(
        URL, {"full_name": "   ", "phone": "0901234567"}, format="json"
    )

    assert response.status_code == 400
    assert "full_name" in response.json()


def test_duplicate_phone_returns_409(api_client):
    payload = {"full_name": "A", "phone": "0901234567"}
    api_client.post(URL, payload, format="json")

    response = api_client.post(URL, payload, format="json")

    assert response.status_code == 409
    assert "detail" in response.json()
    assert Driver.objects.count() == 1


def test_client_cannot_set_approval_status(api_client):
    response = api_client.post(
        URL,
        {"full_name": "A", "phone": "0901234567", "approval_status": "approved"},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["approval_status"] == "pending"


@pytest.fixture
def driver() -> Driver:
    return register_driver(full_name="Nguyen Van A", phone="0901234567")


def test_get_driver_returns_200(api_client, driver):
    response = api_client.get(f"{URL}{driver.id}/")

    assert response.status_code == 200
    assert response.json()["phone"] == "0901234567"


def test_get_unknown_driver_returns_404(api_client):
    assert api_client.get(f"{URL}999999/").status_code == 404


def test_approve_pending_driver_returns_200(api_client, driver):
    response = api_client.post(f"{URL}{driver.id}/approve/")

    assert response.status_code == 200
    assert response.json()["approval_status"] == "approved"
    driver.refresh_from_db()
    assert driver.approval_status == ApprovalStatus.APPROVED


def test_approve_twice_returns_409(api_client, driver):
    api_client.post(f"{URL}{driver.id}/approve/")

    response = api_client.post(f"{URL}{driver.id}/approve/")

    assert response.status_code == 409
    assert "detail" in response.json()


def test_approve_unknown_driver_returns_404(api_client):
    assert api_client.post(f"{URL}999999/approve/").status_code == 404
