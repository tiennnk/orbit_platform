import json
from types import SimpleNamespace

import openai
import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.assistant import providers, services
from apps.food.tests.conftest import CENTER

pytestmark = pytest.mark.django_db

URL = "/api/v1/assistant/chat/"
MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"


def call(name, arguments, call_id="call_1"):
    return SimpleNamespace(
        id=call_id, function=SimpleNamespace(name=name, arguments=arguments)
    )


def completion(content=None, tool_calls=None, finish_reason="stop", refusal=None):
    message = SimpleNamespace(content=content, refusal=refusal, tool_calls=tool_calls)
    return SimpleNamespace(
        choices=[SimpleNamespace(finish_reason=finish_reason, message=message)]
    )


@pytest.fixture
def model(monkeypatch, settings):
    settings.ASSISTANT_PROVIDER = "openai"
    settings.ASSISTANT_MODEL = MODEL
    settings.ASSISTANT_API_KEY = "test-key"
    calls = []

    def fake_create(**params):
        calls.append(params)
        return model.responses.pop(0)

    model.responses = []
    model.calls = calls
    monkeypatch.setattr(providers, "_create_completion", fake_create)
    return model


def ask(client, content="hi", **extra):
    return client.post(
        URL,
        {"messages": [{"role": "user", "content": content}], **extra},
        format="json",
    )


def test_plain_reply(customer_client, model):
    model.responses = [completion("Xin chao!")]

    response = ask(customer_client, "chao ban")

    assert response.json() == {"reply": "Xin chao!"}
    sent = model.calls[0]
    assert sent["model"] == MODEL
    assert sent["messages"][0] == {"role": "system", "content": services.SYSTEM_PROMPT}
    assert sent["messages"][1] == {"role": "user", "content": "chao ban"}
    assert sent["tools"][0]["type"] == "function"
    assert {tool["function"]["name"] for tool in sent["tools"]} == {
        "search_restaurants",
        "get_menu",
        "list_my_orders",
    }


def test_tool_call_loop(customer_client, model, shop):
    arguments = json.dumps({"dish": "com"})
    model.responses = [
        completion(tool_calls=[call("search_restaurants", arguments)]),
        completion("Com suon 45,000."),
    ]

    response = ask(customer_client, "com", latitude=CENTER[0], longitude=CENTER[1])

    assert response.json()["reply"] == "Com suon 45,000."
    assistant, result = model.calls[1]["messages"][2:]
    assert assistant == {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "search_restaurants", "arguments": arguments},
            }
        ],
    }
    assert result["role"] == "tool"
    assert result["tool_call_id"] == "call_1"
    found = json.loads(result["content"])["restaurants"]
    assert [r["id"] for r in found] == [shop.id]


def test_tool_errors_are_prefixed(customer_client, model):
    model.responses = [
        completion(
            tool_calls=[
                call("get_menu", json.dumps({"restaurant_id": 999}), "a"),
                call("get_menu", "{not json", "b"),
                call("list_my_orders", None, "c"),
            ]
        ),
        completion("Sorry."),
    ]

    ask(customer_client, "menu")

    results = model.calls[1]["messages"][3:]
    assert [r["content"] for r in results[:2]] == [
        "Error: Restaurant 999 not found.",
        "Error: Invalid arguments for get_menu.",
    ]
    assert json.loads(results[2]["content"]) == {"orders": []}


@pytest.mark.parametrize(
    "response",
    [
        completion(finish_reason="content_filter"),
        completion(refusal="I can't help with that."),
    ],
)
def test_refusal(customer_client, model, response):
    model.responses = [response]

    assert ask(customer_client).json()["reply"] == services.REFUSAL_REPLY


def test_api_error_returns_503(customer_client, model, monkeypatch):
    def broken(**params):
        raise openai.OpenAIError("rate limited")

    monkeypatch.setattr(providers, "_create_completion", broken)

    response = ask(customer_client)

    assert response.status_code == 503
    assert response.json()["detail"] == "The assistant is unavailable right now."


def test_empty_choices_returns_503(customer_client, model):
    model.responses = [SimpleNamespace(choices=[])]

    assert ask(customer_client).status_code == 503


def test_missing_key_returns_503(customer_client, model, settings):
    settings.ASSISTANT_API_KEY = ""

    assert ask(customer_client).status_code == 503
    assert model.calls == []


def test_unknown_provider(customer, settings):
    settings.ASSISTANT_PROVIDER = "nope"

    with pytest.raises(ImproperlyConfigured):
        services.reply(user=customer, history=[{"role": "user", "content": "hi"}])
