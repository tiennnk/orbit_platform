import pytest

from apps.food.tests.conftest import CENTER
from apps.shared.domain import ApprovalStatus

pytestmark = pytest.mark.django_db

URL = "/api/v1/food/restaurants/nearby/"


def search(client, **params):
    query = {"latitude": CENTER[0], "longitude": CENTER[1], **params}
    response = client.get(URL, query)
    assert response.status_code == 200
    return response.json()


def test_returns_closest_first(user_client, make_restaurant):
    far = make_restaurant(3.0)
    near = make_restaurant(0.5)

    body = search(user_client)

    assert [r["id"] for r in body] == [near.id, far.id]
    assert body[0]["distance_km"] == pytest.approx(0.5, abs=0.01)


def test_open_restaurants_come_first(user_client, make_restaurant):
    closed = make_restaurant(0.2, is_open=False)
    opened = make_restaurant(2.0)

    body = search(user_client)

    assert [(r["id"], r["is_open"]) for r in body] == [
        (opened.id, True),
        (closed.id, False),
    ]


def test_only_approved_restaurants(user_client, make_restaurant):
    approved = make_restaurant()
    for status in (
        ApprovalStatus.PENDING,
        ApprovalStatus.REJECTED,
        ApprovalStatus.SUSPENDED,
    ):
        make_restaurant(status=status)

    assert [r["id"] for r in search(user_client)] == [approved.id]


def test_radius_and_limit(user_client, make_restaurant):
    inside = [make_restaurant(km) for km in (0.5, 1.0, 1.5)]
    make_restaurant(4.0)

    body = search(user_client, radius_km=2, limit=2)

    assert [r["id"] for r in body] == [inside[0].id, inside[1].id]


def test_filter_by_name(user_client, make_restaurant):
    pho = make_restaurant(name="Pho Hoa Pasteur")
    make_restaurant(name="Com Tam Cali")

    assert [r["id"] for r in search(user_client, q="pho")] == [pho.id]


@pytest.mark.parametrize(
    "params",
    [{"radius_km": 0.1}, {"radius_km": 21}, {"limit": 0}, {"limit": 51}],
)
def test_invalid_params_return_400(user_client, params):
    query = {"latitude": CENTER[0], "longitude": CENTER[1], **params}

    assert user_client.get(URL, query).status_code == 400


def test_anonymous_cannot_search(anon_client):
    response = anon_client.get(URL, {"latitude": CENTER[0], "longitude": CENTER[1]})

    assert response.status_code == 401
