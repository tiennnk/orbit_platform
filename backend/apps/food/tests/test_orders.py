import pytest
from django.db import IntegrityError, transaction

from apps.food.models import FoodOrder
from apps.food.tests.conftest import CENTER, KM_IN_LAT_DEGREES
from apps.rides.models import RideOffer
from conftest import _client_for

pytestmark = pytest.mark.django_db

URL = "/api/v1/food/orders/"
SHOP_ORDERS_URL = "/api/v1/food/restaurants/me/orders/"


def place(client, payload):
    response = client.post(URL, payload, format="json")
    assert response.status_code == 201, response.json()
    return response.json()


def accept(owner_client, order_id):
    return owner_client.post(f"{SHOP_ORDERS_URL}{order_id}/accept/")


def test_place_order(customer_client, order_payload):
    body = place(customer_client, order_payload)

    assert body["status"] == "placed"
    assert body["subtotal"] == 2 * 45000 + 5000
    assert body["delivery_fee"] == 24000
    assert body["total"] == body["subtotal"] + body["delivery_fee"]
    assert body["delivery"] is None
    assert body["note"] == "No chili"
    lines = [
        (line["name"], line["quantity"], line["line_total"]) for line in body["lines"]
    ]
    assert lines == [("Com suon", 2, 90000), ("Tra da", 1, 5000)]


def test_order_keeps_prices_at_checkout(customer_client, order_payload, shop):
    body = place(customer_client, order_payload)
    shop.menu_items.update(price=99000)
    shop.menu_items.get(name="Tra da").delete()

    again = customer_client.get(f"{URL}{body['id']}/").json()

    assert again["subtotal"] == body["subtotal"]
    assert sorted(line["unit_price"] for line in again["lines"]) == [5000, 45000]


def test_quote_matches_order_fee(customer_client, order_payload, shop):
    quote = customer_client.get(
        f"/api/v1/food/restaurants/{shop.id}/delivery-quote/",
        {
            "latitude": order_payload["delivery_latitude"],
            "longitude": order_payload["delivery_longitude"],
        },
    ).json()

    assert quote == {"distance_km": 2.6, "delivery_fee": 24000, "deliverable": True}


def test_quote_flags_far_addresses(customer_client, shop):
    quote = customer_client.get(
        f"/api/v1/food/restaurants/{shop.id}/delivery-quote/",
        {"latitude": CENTER[0] + 20 * KM_IN_LAT_DEGREES, "longitude": CENTER[1]},
    ).json()

    assert quote["deliverable"] is False


def test_closed_restaurant_returns_409(customer_client, order_payload, shop):
    shop.is_open = False
    shop.save()

    assert customer_client.post(URL, order_payload, format="json").status_code == 409


def test_unapproved_restaurant_returns_404(customer_client, order_payload, shop):
    shop.is_open = False
    shop.approval_status = "suspended"
    shop.save()

    assert customer_client.post(URL, order_payload, format="json").status_code == 404


def test_owner_cannot_order_from_own_restaurant(owner_client, order_payload):
    assert owner_client.post(URL, order_payload, format="json").status_code == 409


def test_dish_from_another_restaurant_returns_409(
    customer_client, order_payload, make_restaurant
):
    stranger = make_restaurant().menu_items.create(name="Pho", price=50000)
    order_payload["items"].append({"menu_item_id": stranger.id, "quantity": 1})

    response = customer_client.post(URL, order_payload, format="json")

    assert response.status_code == 409
    assert not FoodOrder.objects.exists()


def test_sold_out_dish_returns_409(customer_client, order_payload, shop):
    shop.menu_items.filter(name="Tra da").update(is_available=False)

    response = customer_client.post(URL, order_payload, format="json")

    assert response.status_code == 409
    assert "Tra da" in response.json()["detail"]


def test_too_far_returns_409(customer_client, order_payload):
    order_payload["delivery_latitude"] = CENTER[0] + 20 * KM_IN_LAT_DEGREES

    assert customer_client.post(URL, order_payload, format="json").status_code == 409


@pytest.mark.parametrize(
    "items",
    [
        [],
        [{"menu_item_id": 1, "quantity": 0}],
        [{"menu_item_id": 1, "quantity": 21}],
        [{"menu_item_id": 1, "quantity": 1}, {"menu_item_id": 1, "quantity": 2}],
    ],
)
def test_invalid_items_return_400(customer_client, order_payload, items):
    order_payload["items"] = items

    response = customer_client.post(URL, order_payload, format="json")

    assert response.status_code == 400
    assert "items" in response.json()


def test_anonymous_cannot_order(anon_client, order_payload):
    assert anon_client.post(URL, order_payload, format="json").status_code == 401


def test_customer_sees_only_own_orders(customer_client, other_client, order_payload):
    order = place(customer_client, order_payload)

    assert customer_client.get(URL).json()["count"] == 1
    assert other_client.get(URL).json()["count"] == 0
    assert other_client.get(f"{URL}{order['id']}/").status_code == 404


def test_owner_can_view_order(customer_client, owner_client, order_payload):
    order = place(customer_client, order_payload)

    assert owner_client.get(f"{URL}{order['id']}/").status_code == 200


def test_customer_cancels_new_order(customer_client, order_payload):
    order = place(customer_client, order_payload)

    response = customer_client.post(f"{URL}{order['id']}/cancel/")

    assert response.json()["status"] == "cancelled"
    assert response.json()["closed_at"] is not None


def test_cannot_cancel_after_restaurant_accepts(
    customer_client, owner_client, order_payload
):
    order = place(customer_client, order_payload)
    accept(owner_client, order["id"])

    assert customer_client.post(f"{URL}{order['id']}/cancel/").status_code == 409


def test_stranger_cannot_cancel(customer_client, other_client, order_payload):
    order = place(customer_client, order_payload)

    assert other_client.post(f"{URL}{order['id']}/cancel/").status_code == 404


def test_restaurant_rejects_order(customer_client, owner_client, order_payload):
    order = place(customer_client, order_payload)

    response = owner_client.post(f"{SHOP_ORDERS_URL}{order['id']}/reject/")

    assert response.json()["status"] == "rejected"
    assert accept(owner_client, order["id"]).status_code == 409


def test_other_restaurant_cannot_touch_order(
    customer_client, order_payload, make_restaurant, django_user_model
):
    order = place(customer_client, order_payload)
    rival = django_user_model.objects.create_user(username="rival")
    make_restaurant(owner=rival)

    assert accept(_client_for(rival), order["id"]).status_code == 404


def test_full_delivery_flow(customer_client, owner_client, order_payload, make_courier):
    courier = make_courier()
    courier_client = _client_for(courier.user)
    order = place(customer_client, order_payload)

    accepted = accept(owner_client, order["id"]).json()
    assert accepted["status"] == "accepted"
    assert accepted["delivery"]["status"] == "searching"

    offer = courier_client.get("/api/v1/rides/offers/current/").json()
    assert offer["ride"]["service"] == "food"
    assert offer["ride"]["pickup_label"].startswith("Restaurant")
    assert offer["ride"]["dropoff_label"] == "12 Nguyen Hue"
    courier_client.post(f"/api/v1/rides/offers/{offer['id']}/accept/")

    tracked = customer_client.get(f"{URL}{order['id']}/").json()
    assert tracked["delivery"]["status"] == "assigned"
    assert tracked["delivery"]["driver"]["id"] == courier.id

    ride_id = tracked["delivery"]["id"]
    assert (
        customer_client.get(f"/api/v1/rides/{ride_id}/driver-position/").status_code
        == 200
    )
    courier_client.post(f"/api/v1/rides/{ride_id}/start/")
    courier_client.post(f"/api/v1/rides/{ride_id}/complete/")

    done = customer_client.get(f"{URL}{order['id']}/").json()
    assert done["delivery"]["status"] == "completed"
    assert owner_client.get(SHOP_ORDERS_URL).json()["count"] == 0
    assert owner_client.get(SHOP_ORDERS_URL, {"active": "false"}).json()["count"] == 1


def test_no_courier_then_redispatch(
    customer_client, owner_client, order_payload, make_courier
):
    order = place(customer_client, order_payload)

    accepted = accept(owner_client, order["id"]).json()
    assert accepted["delivery"]["status"] == "no_driver"
    assert owner_client.get(SHOP_ORDERS_URL).json()["count"] == 1

    courier = make_courier()
    response = owner_client.post(f"{SHOP_ORDERS_URL}{order['id']}/redispatch/")

    assert response.json()["delivery"]["status"] == "searching"
    assert response.json()["delivery"]["id"] != accepted["delivery"]["id"]
    assert RideOffer.objects.get(status="pending").driver_id == courier.id


def test_redispatch_while_searching_returns_409(
    customer_client, owner_client, order_payload, make_courier
):
    make_courier()
    order = place(customer_client, order_payload)
    accept(owner_client, order["id"])

    response = owner_client.post(f"{SHOP_ORDERS_URL}{order['id']}/redispatch/")

    assert response.status_code == 409


def test_restaurant_order_lists(customer_client, owner_client, order_payload):
    first = place(customer_client, order_payload)
    second = place(customer_client, order_payload)
    customer_client.post(f"{URL}{second['id']}/cancel/")

    active = owner_client.get(SHOP_ORDERS_URL).json()["results"]
    done = owner_client.get(SHOP_ORDERS_URL, {"active": "false"}).json()["results"]

    assert [o["id"] for o in active] == [first["id"]]
    assert [o["id"] for o in done] == [second["id"]]


def test_shop_orders_require_restaurant(customer_client):
    assert customer_client.get(SHOP_ORDERS_URL).status_code == 404


def test_delivery_does_not_block_rides(
    customer_client, owner_client, order_payload, make_courier
):
    make_courier()
    order = place(customer_client, order_payload)
    accept(owner_client, order["id"])
    make_courier(1.0)

    assert customer_client.get("/api/v1/rides/current/").status_code == 404
    ride = customer_client.post(
        "/api/v1/rides/",
        {
            "pickup_latitude": CENTER[0],
            "pickup_longitude": CENTER[1],
            "dropoff_latitude": CENTER[0] + 0.05,
            "dropoff_longitude": CENTER[1],
        },
        format="json",
    )
    assert ride.status_code == 201
    assert ride.json()["service"] == "ride"


def test_customer_cannot_cancel_delivery_ride_directly(
    customer_client, owner_client, order_payload, make_courier
):
    make_courier()
    order = place(customer_client, order_payload)
    ride_id = accept(owner_client, order["id"]).json()["delivery"]["id"]

    response = customer_client.post(f"/api/v1/rides/{ride_id}/cancel/")

    assert response.status_code == 409


def test_deliveries_stay_out_of_ride_history(
    customer_client, owner_client, order_payload
):
    order = place(customer_client, order_payload)
    accept(owner_client, order["id"])

    assert customer_client.get("/api/v1/rides/history/").json()["count"] == 0


def test_db_rejects_wrong_total(customer, shop):
    with pytest.raises(IntegrityError), transaction.atomic():
        FoodOrder.objects.create(
            customer=customer,
            restaurant=shop,
            delivery_latitude=CENTER[0],
            delivery_longitude=CENTER[1],
            subtotal=1000,
            delivery_fee=500,
            total=999,
        )
