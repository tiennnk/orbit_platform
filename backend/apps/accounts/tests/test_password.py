import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from conftest import PASSWORD

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/password/"
NEW_PASSWORD = "orbit-rider-2027"


@pytest.fixture
def token_client(user):
    token = Token.objects.create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client, token.key


def test_change_password_rotates_token(user, token_client):
    client, old_token = token_client

    response = client.post(
        URL,
        {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        format="json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["id"] == user.id
    assert body["token"] != old_token
    assert list(Token.objects.filter(user=user).values_list("key", flat=True)) == [
        body["token"]
    ]
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)


def test_old_token_stops_working(token_client):
    client, _ = token_client
    client.post(
        URL,
        {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        format="json",
    )

    assert client.get("/api/v1/auth/me/").status_code == 401


def test_can_log_in_with_new_password_only(anon_client, user, token_client):
    client, _ = token_client
    client.post(
        URL,
        {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        format="json",
    )
    login = "/api/v1/auth/login/"

    old = anon_client.post(
        login, {"username": user.username, "password": PASSWORD}, format="json"
    )
    new = anon_client.post(
        login, {"username": user.username, "password": NEW_PASSWORD}, format="json"
    )

    assert old.status_code == 401
    assert new.status_code == 200


def test_wrong_current_password_returns_400(user, user_client):
    response = user_client.post(
        URL,
        {"current_password": "not-it", "new_password": NEW_PASSWORD},
        format="json",
    )

    assert response.status_code == 400
    assert "current_password" in response.json()
    user.refresh_from_db()
    assert user.check_password(PASSWORD)


@pytest.mark.parametrize("new_password", ["123", "password", PASSWORD])
def test_rejects_weak_or_same_password(user, user_client, new_password):
    response = user_client.post(
        URL,
        {"current_password": PASSWORD, "new_password": new_password},
        format="json",
    )

    assert response.status_code == 400
    assert "new_password" in response.json()
    user.refresh_from_db()
    assert user.check_password(PASSWORD)


def test_rejects_password_like_username(django_user_model):
    user = django_user_model.objects.create_user(
        username="nguyenvana", password=PASSWORD
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        URL,
        {"current_password": PASSWORD, "new_password": "nguyenvana1"},
        format="json",
    )

    assert response.status_code == 400


def test_anonymous_cannot_change_password(anon_client):
    response = anon_client.post(
        URL,
        {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        format="json",
    )

    assert response.status_code == 401
