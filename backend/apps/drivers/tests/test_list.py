import pytest

from apps.drivers.services import approve_driver, register_driver

pytestmark = pytest.mark.django_db

URL = "/api/v1/drivers/"


@pytest.fixture
def drivers(django_user_model):
    created = []
    for n in range(3):
        user = django_user_model.objects.create_user(username=f"listed{n}")
        created.append(
            register_driver(user=user, full_name=f"Driver {n}", phone=f"090000000{n}")
        )
    approve_driver(driver_id=created[1].id)
    return created


def test_staff_lists_drivers_oldest_first(staff_client, drivers):
    response = staff_client.get(URL)

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert [d["id"] for d in body["results"]] == [d.id for d in drivers]


def test_filter_by_approval_status(staff_client, drivers):
    response = staff_client.get(URL, {"approval_status": "pending"})

    assert [d["id"] for d in response.json()["results"]] == [
        drivers[0].id,
        drivers[2].id,
    ]


def test_invalid_filter_returns_400(staff_client, drivers):
    response = staff_client.get(URL, {"approval_status": "nope"})

    assert response.status_code == 400
    assert "approval_status" in response.json()


def test_pagination(staff_client, drivers):
    first = staff_client.get(URL, {"page_size": 2}).json()
    second = staff_client.get(URL, {"page_size": 2, "page": 2}).json()

    assert len(first["results"]) == 2
    assert first["next"] is not None
    assert [d["id"] for d in second["results"]] == [drivers[2].id]
    assert second["next"] is None


def test_non_staff_cannot_list_drivers(user_client, drivers):
    assert user_client.get(URL).status_code == 403


def test_non_staff_can_still_register(user_client):
    response = user_client.post(
        URL, {"full_name": "New Driver", "phone": "0911111111"}, format="json"
    )

    assert response.status_code == 201
