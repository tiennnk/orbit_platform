import json
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from apps.assistant import providers, services
from apps.food.tests.conftest import CENTER

pytestmark = pytest.mark.django_db

URL = "/api/v1/assistant/chat/"


def text(content):
    return SimpleNamespace(type="text", text=content)


def tool_use(name, arguments, block_id="call_1"):
    return SimpleNamespace(type="tool_use", id=block_id, name=name, input=arguments)


def message(*blocks, stop_reason="end_turn"):
    return SimpleNamespace(content=list(blocks), stop_reason=stop_reason)


@pytest.fixture
def model(monkeypatch, settings):
    settings.ASSISTANT_PROVIDER = "anthropic"
    settings.ASSISTANT_MODEL = "claude-opus-5-5"
    calls = []

    def fake_create(**params):
        calls.append(params)
        return model.responses.pop(0)

    model.responses = []
    model.calls = calls
    monkeypatch.setattr(providers, "_create_message", fake_create)
    return model


def ask(client, *turns, **extra):
    roles = ["user", "assistant"]
    history = [{"role": roles[n % 2], "content": turn} for n, turn in enumerate(turns)]
    return client.post(URL, {"messages": history, **extra}, format="json")


def tool_results(call):
    return call["messages"][-1]["content"]


def test_plain_reply(customer_client, model):
    model.responses = [message(text("Xin chao!"))]

    response = ask(customer_client, "chao ban")

    assert response.status_code == 200
    assert response.json() == {"reply": "Xin chao!"}
    sent = model.calls[0]
    assert sent["messages"] == [{"role": "user", "content": "chao ban"}]
    assert {tool["name"] for tool in sent["tools"]} == {
        "search_restaurants",
        "get_menu",
        "list_my_orders",
    }


def test_history_is_forwarded(customer_client, model):
    model.responses = [message(text("Pho Hoa."))]

    ask(customer_client, "tim quan pho", "Ban o dau?", "quan 1")

    assert [turn["role"] for turn in model.calls[0]["messages"]] == [
        "user",
        "assistant",
        "user",
    ]


def test_tool_call_loop(customer_client, model, shop):
    model.responses = [
        message(
            text("Let me look."),
            tool_use("search_restaurants", {"dish": "com"}),
            stop_reason="tool_use",
        ),
        message(text("Restaurant has com suon for 45,000.")),
    ]

    response = ask(
        customer_client, "com gan day", latitude=CENTER[0], longitude=CENTER[1]
    )

    assert response.json()["reply"] == "Restaurant has com suon for 45,000."
    second = model.calls[1]
    assert second["messages"][1]["role"] == "assistant"
    [result] = tool_results(second)
    assert result["tool_use_id"] == "call_1"
    assert result["is_error"] is False
    found = json.loads(result["content"])["restaurants"]
    assert [r["id"] for r in found] == [shop.id]
    assert [d["name"] for d in found[0]["matching_dishes"]] == ["Com suon"]


def test_parallel_tool_calls_answered_together(customer_client, model, shop):
    model.responses = [
        message(
            tool_use("get_menu", {"restaurant_id": shop.id}, "a"),
            tool_use("list_my_orders", {}, "b"),
            stop_reason="tool_use",
        ),
        message(text("Done.")),
    ]

    ask(customer_client, "menu and orders")

    results = tool_results(model.calls[1])
    assert [r["tool_use_id"] for r in results] == ["a", "b"]
    assert all(r["is_error"] is False for r in results)


def test_tool_error_is_reported_to_model(customer_client, model):
    model.responses = [
        message(tool_use("get_menu", {"restaurant_id": 999}), stop_reason="tool_use"),
        message(text("That restaurant does not exist.")),
    ]

    ask(customer_client, "menu 999")

    [result] = tool_results(model.calls[1])
    assert result["is_error"] is True
    assert result["content"] == "Restaurant 999 not found."


def test_unknown_tool_and_bad_arguments(customer_client, model):
    model.responses = [
        message(
            tool_use("cancel_order", {"order_id": 1}, "a"),
            tool_use("get_menu", {"id": 1}, "b"),
            stop_reason="tool_use",
        ),
        message(text("Sorry.")),
    ]

    ask(customer_client, "cancel my order")

    results = tool_results(model.calls[1])
    assert [r["content"] for r in results] == [
        "Unknown tool cancel_order.",
        "Invalid arguments for get_menu.",
    ]


def test_search_without_location(customer_client, model, shop):
    model.responses = [
        message(tool_use("search_restaurants", {}), stop_reason="tool_use"),
        message(text("Where are you?")),
    ]

    ask(customer_client, "quan gan day")

    [result] = tool_results(model.calls[1])
    assert result["is_error"] is True
    assert result["content"] == "The customer's location is unknown."


def test_loop_stops_after_max_rounds(customer_client, model):
    model.responses = [
        message(tool_use("list_my_orders", {}), stop_reason="tool_use")
        for _ in range(services.MAX_TOOL_ROUNDS)
    ]

    response = ask(customer_client, "orders")

    assert response.json()["reply"] == services.GAVE_UP_REPLY
    assert len(model.calls) == services.MAX_TOOL_ROUNDS


def test_refusal(customer_client, model):
    model.responses = [message(stop_reason="refusal")]

    assert ask(customer_client, "...").json()["reply"] == services.REFUSAL_REPLY


def test_empty_answer_falls_back(customer_client, model):
    model.responses = [message()]

    assert ask(customer_client, "hi").json()["reply"] == services.GAVE_UP_REPLY


def test_model_failure_returns_503(customer_client, model, monkeypatch):
    def broken(**params):
        raise anthropic.APIConnectionError(
            request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
        )

    monkeypatch.setattr(providers, "_create_message", broken)

    response = ask(customer_client, "hi")

    assert response.status_code == 503
    assert response.json()["detail"] == "The assistant is unavailable right now."


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"messages": []},
        {"messages": [{"role": "assistant", "content": "hi"}]},
        {
            "messages": [
                {"role": "user", "content": "a"},
                {"role": "assistant", "content": "b"},
            ]
        },
        {
            "messages": [
                {"role": "user", "content": "a"},
                {"role": "user", "content": "b"},
            ]
        },
        {"messages": [{"role": "system", "content": "a"}]},
        {"messages": [{"role": "user", "content": "x" * 1001}]},
        {"messages": [{"role": "user", "content": "   "}]},
        {"messages": [{"role": "user", "content": "a"}], "latitude": 10.7},
    ],
)
def test_invalid_payload_returns_400(customer_client, model, payload):
    assert customer_client.post(URL, payload, format="json").status_code == 400
    assert model.calls == []


def test_too_many_turns_returns_400(customer_client, model):
    turns = ["q", "a"] * 10 + ["q"]

    assert ask(customer_client, *turns).status_code == 400


def test_anonymous_cannot_chat(anon_client, model):
    assert ask(anon_client, "hi").status_code == 401


def test_chat_is_throttled(customer_client, model):
    model.responses = [message(text("ok")) for _ in range(10)]

    statuses = [ask(customer_client, "hi").status_code for _ in range(11)]

    assert statuses == [200] * 10 + [429]


def test_search_folds_accents_and_filters_price(
    customer_client, model, make_restaurant
):
    cheap = make_restaurant(1, name="Phở Hòa")
    cheap.menu_items.create(name="Phở bò tái", price=45000)
    pricey = make_restaurant(2, name="Phở Lệ")
    pricey.menu_items.create(name="Phở đặc biệt", price=90000)
    model.responses = [
        message(
            tool_use("search_restaurants", {"dish": "pho", "max_price": 50000}),
            stop_reason="tool_use",
        ),
        message(text("ok")),
    ]

    ask(customer_client, "pho duoi 50k", latitude=CENTER[0], longitude=CENTER[1])

    found = json.loads(tool_results(model.calls[1])[0]["content"])["restaurants"]
    assert [r["name"] for r in found] == ["Phở Hòa"]


def test_search_by_name_skips_far_and_unapproved(
    customer_client, model, make_restaurant
):
    near = make_restaurant(1, name="Com Tam Cali")
    make_restaurant(8, name="Com Tam Far")
    make_restaurant(1, name="Com Tam Pending", status="pending")
    model.responses = [
        message(
            tool_use("search_restaurants", {"name": "cơm tấm"}), stop_reason="tool_use"
        ),
        message(text("ok")),
    ]

    ask(customer_client, "com tam", latitude=CENTER[0], longitude=CENTER[1])

    found = json.loads(tool_results(model.calls[1])[0]["content"])["restaurants"]
    assert [r["id"] for r in found] == [near.id]
    assert found[0]["distance_km"] == pytest.approx(1.0, abs=0.1)


def test_orders_tool_only_sees_own_orders(
    customer_client, other_client, model, order_payload
):
    mine = customer_client.post("/api/v1/food/orders/", order_payload, format="json")
    other_client.post("/api/v1/food/orders/", order_payload, format="json")
    model.responses = [
        message(tool_use("list_my_orders", {"limit": 50}), stop_reason="tool_use"),
        message(text("ok")),
    ]

    ask(customer_client, "don cua toi")

    orders = json.loads(tool_results(model.calls[1])[0]["content"])["orders"]
    assert [o["id"] for o in orders] == [mine.json()["id"]]
    assert orders[0]["status"] == "placed"
    assert orders[0]["delivery_status"] is None
    assert orders[0]["items"] == ["2 x Com suon", "1 x Tra da"]


def test_menu_hides_unapproved_restaurant(customer_client, model, make_restaurant):
    pending = make_restaurant(status="pending")
    model.responses = [
        message(
            tool_use("get_menu", {"restaurant_id": pending.id}), stop_reason="tool_use"
        ),
        message(text("ok")),
    ]

    ask(customer_client, "menu")

    assert tool_results(model.calls[1])[0]["is_error"] is True


def test_default_model_uses_refusal_fallback(customer_client, model):
    model.responses = [message(text("ok"))]

    ask(customer_client, "hi")

    assert model.calls[0]["model"] == "claude-opus-5-5"
    assert model.calls[0]["fallbacks"] == "default"


def test_model_without_fallback_support(customer_client, model, settings):
    settings.ASSISTANT_MODEL = "claude-haiku-5-5"
    model.responses = [message(text("ok"))]

    ask(customer_client, "hi")

    assert model.calls[0]["model"] == "claude-haiku-5-5"
    assert "fallbacks" not in model.calls[0]
    assert "betas" not in model.calls[0]


def test_location_is_not_sent_to_model(customer_client, model):
    model.responses = [message(text("ok"))]

    ask(customer_client, "hi", latitude=CENTER[0], longitude=CENTER[1])

    assert str(CENTER[0]) not in json.dumps(model.calls[0]["messages"])
