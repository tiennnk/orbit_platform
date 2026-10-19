import pytest
from django.db import IntegrityError, transaction

from apps.food.domain import InvalidRestaurantTransition
from apps.food.models import Restaurant
from apps.shared.domain import ApprovalStatus

pytestmark = pytest.mark.django_db

URL = "/api/v1/food/restaurants/"
ME_URL = f"{URL}me/"


def test_register_restaurant(owner_client, profile):
    response = owner_client.post(URL, profile, format="json")

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == profile["name"]
    assert body["approval_status"] == "pending"
    assert body["is_open"] is False


def test_register_strips_whitespace(owner_client, profile):
    profile["name"] = "  Pho Hoa  "

    assert owner_client.post(URL, profile, format="json").json()["name"] == "Pho Hoa"


def test_one_restaurant_per_account(owner_client, profile):
    owner_client.post(URL, profile, format="json")

    response = owner_client.post(URL, profile, format="json")

    assert response.status_code == 409
    assert Restaurant.objects.count() == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [("latitude", 91), ("longitude", -181), ("name", ""), ("phone", "x" * 21)],
)
def test_register_rejects_bad_input(owner_client, profile, field, value):
    profile[field] = value

    response = owner_client.post(URL, profile, format="json")

    assert response.status_code == 400
    assert field in response.json()


def test_anonymous_cannot_register(anon_client, profile):
    assert anon_client.post(URL, profile, format="json").status_code == 401


def test_my_restaurant_includes_menu(owner, owner_client, make_restaurant):
    restaurant = make_restaurant(owner=owner)
    restaurant.menu_items.create(name="Com suon", price=45000)

    body = owner_client.get(ME_URL).json()

    assert body["id"] == restaurant.id
    assert [item["name"] for item in body["menu"]] == ["Com suon"]


def test_no_restaurant_returns_404(owner_client):
    assert owner_client.get(ME_URL).status_code == 404


def test_edit_rejected_profile_resubmits(owner, owner_client, make_restaurant, profile):
    make_restaurant(owner=owner, status=ApprovalStatus.REJECTED)
    profile["name"] = "Fixed Name"

    response = owner_client.put(ME_URL, profile, format="json")

    assert response.status_code == 200
    assert response.json()["name"] == "Fixed Name"
    assert response.json()["approval_status"] == "pending"


def test_cannot_edit_approved_profile(owner, owner_client, make_restaurant, profile):
    make_restaurant(owner=owner)

    assert owner_client.put(ME_URL, profile, format="json").status_code == 409


def test_open_and_close(owner, owner_client, make_restaurant):
    make_restaurant(owner=owner, is_open=False)

    assert owner_client.post(f"{ME_URL}open/").json()["is_open"] is True
    assert owner_client.post(f"{ME_URL}close/").json()["is_open"] is False


def test_pending_restaurant_cannot_open(owner, owner_client, make_restaurant):
    make_restaurant(owner=owner, status=ApprovalStatus.PENDING)

    assert owner_client.post(f"{ME_URL}open/").status_code == 409


def test_staff_lists_restaurants_by_status(staff_client, make_restaurant):
    pending = make_restaurant(status=ApprovalStatus.PENDING)
    make_restaurant()

    body = staff_client.get(URL, {"approval_status": "pending"}).json()

    assert body["count"] == 1
    assert body["results"][0]["id"] == pending.id


def test_non_staff_cannot_list_restaurants(owner_client):
    assert owner_client.get(URL).status_code == 403


@pytest.mark.parametrize(
    ("start", "action", "expected"),
    [
        (ApprovalStatus.PENDING, "approve", "approved"),
        (ApprovalStatus.PENDING, "reject", "rejected"),
        (ApprovalStatus.APPROVED, "suspend", "suspended"),
        (ApprovalStatus.SUSPENDED, "reinstate", "approved"),
    ],
)
def test_staff_moderation(staff_client, make_restaurant, start, action, expected):
    restaurant = make_restaurant(status=start)

    response = staff_client.post(f"{URL}{restaurant.id}/{action}/")

    assert response.status_code == 200
    assert response.json()["approval_status"] == expected


def test_suspend_closes_restaurant(staff_client, make_restaurant):
    restaurant = make_restaurant()

    assert (
        staff_client.post(f"{URL}{restaurant.id}/suspend/").json()["is_open"] is False
    )


def test_invalid_moderation_returns_409(staff_client, make_restaurant):
    restaurant = make_restaurant()

    assert staff_client.post(f"{URL}{restaurant.id}/approve/").status_code == 409


def test_moderating_missing_restaurant_returns_404(staff_client):
    assert staff_client.post(f"{URL}999999/approve/").status_code == 404


def test_non_staff_cannot_moderate(owner_client, make_restaurant):
    restaurant = make_restaurant(status=ApprovalStatus.PENDING)

    assert owner_client.post(f"{URL}{restaurant.id}/approve/").status_code == 403


def test_public_detail_shows_approved_only(owner_client, make_restaurant):
    approved = make_restaurant()
    pending = make_restaurant(status=ApprovalStatus.PENDING)

    assert owner_client.get(f"{URL}{approved.id}/").status_code == 200
    assert owner_client.get(f"{URL}{pending.id}/").status_code == 404


@pytest.mark.parametrize("action", ["approve", "reject", "suspend", "reinstate"])
def test_domain_transitions_reject_wrong_state(make_restaurant, action):
    restaurant = make_restaurant(status=ApprovalStatus.REJECTED)

    with pytest.raises(InvalidRestaurantTransition):
        getattr(restaurant, action)()


def test_db_rejects_open_unapproved_restaurant(make_restaurant):
    restaurant = make_restaurant(status=ApprovalStatus.PENDING)

    with pytest.raises(IntegrityError), transaction.atomic():
        Restaurant.objects.filter(pk=restaurant.pk).update(is_open=True)
