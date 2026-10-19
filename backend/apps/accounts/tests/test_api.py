import pytest
from rest_framework.authtoken.models import Token

from conftest import PASSWORD

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
LOGOUT_URL = "/api/v1/auth/logout/"
ME_URL = "/api/v1/auth/me/"

GOOD_PASSWORD = "orbit-rider-2026"


def test_register_returns_token_and_user(anon_client, django_user_model):
    response = anon_client.post(
        REGISTER_URL, {"username": "rider9", "password": GOOD_PASSWORD}, format="json"
    )

    assert response.status_code == 201
    body = response.json()
    user = django_user_model.objects.get(username="rider9")
    assert body["user"] == {"id": user.id, "username": "rider9", "is_staff": False}
    assert Token.objects.get(user=user).key == body["token"]
    assert user.check_password(GOOD_PASSWORD)


def test_register_rejects_weak_password(anon_client, django_user_model):
    response = anon_client.post(
        REGISTER_URL, {"username": "rider9", "password": "123"}, format="json"
    )

    assert response.status_code == 400
    assert not django_user_model.objects.filter(username="rider9").exists()


def test_register_rejects_taken_username_case_insensitive(anon_client, user):
    response = anon_client.post(
        REGISTER_URL,
        {"username": user.username.upper(), "password": GOOD_PASSWORD},
        format="json",
    )

    assert response.status_code == 400
    assert "username" in response.json()


def test_register_cannot_create_staff(anon_client, django_user_model):
    anon_client.post(
        REGISTER_URL,
        {"username": "sneaky", "password": GOOD_PASSWORD, "is_staff": True},
        format="json",
    )

    assert django_user_model.objects.get(username="sneaky").is_staff is False


def test_login_returns_token_and_user(anon_client, user):
    response = anon_client.post(
        LOGIN_URL, {"username": user.username, "password": PASSWORD}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["user"]["username"] == user.username
    assert response.json()["token"]


def test_login_twice_returns_same_token(anon_client, user):
    payload = {"username": user.username, "password": PASSWORD}

    first = anon_client.post(LOGIN_URL, payload, format="json").json()["token"]
    second = anon_client.post(LOGIN_URL, payload, format="json").json()["token"]

    assert first == second


def test_wrong_password_returns_401(anon_client, user):
    response = anon_client.post(
        LOGIN_URL, {"username": user.username, "password": "wrong"}, format="json"
    )

    assert response.status_code == 401
    assert "token" not in response.json()


def test_login_works_even_with_stale_token_header(anon_client, user):
    anon_client.credentials(HTTP_AUTHORIZATION="Token expired-or-deleted")

    response = anon_client.post(
        LOGIN_URL, {"username": user.username, "password": PASSWORD}, format="json"
    )

    assert response.status_code == 200


def test_me_returns_current_user(user_client, user):
    response = user_client.get(ME_URL)

    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "username": user.username,
        "is_staff": False,
    }


def test_me_shows_staff_flag(staff_client):
    assert staff_client.get(ME_URL).json()["is_staff"] is True


def test_me_requires_auth(anon_client):
    assert anon_client.get(ME_URL).status_code == 401


def test_logout_invalidates_token(anon_client, user):
    token = anon_client.post(
        LOGIN_URL, {"username": user.username, "password": PASSWORD}, format="json"
    ).json()["token"]
    anon_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

    assert anon_client.post(LOGOUT_URL).status_code == 204
    assert anon_client.get(ME_URL).status_code == 401


def test_login_is_rate_limited(anon_client, user):
    payload = {"username": user.username, "password": "wrong"}

    codes = [
        anon_client.post(LOGIN_URL, payload, format="json").status_code
        for _ in range(21)
    ]

    assert codes[:20] == [401] * 20
    assert codes[20] == 429
