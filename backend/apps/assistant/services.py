import json

import anthropic
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser

from apps.assistant.tools import TOOLS, ToolContext, ToolError, run_tool
from apps.shared.exceptions import UnavailableError

MAX_TOOL_ROUNDS = 5
MAX_TOKENS = 4096
FALLBACK_BETA = "server-side-fallback-2026-07-01"
FALLBACK_MODELS = {
    "claude-fable-5-1",
    "claude-opus-5-5",
    "claude-opus-5",
    "claude-sonnet-5-5",
}
REFUSAL_REPLY = "Sorry, I can't help with that."
GAVE_UP_REPLY = "Sorry, I couldn't finish that. Could you ask in a simpler way?"

SYSTEM_PROMPT = """You are the assistant inside Orbit, an app for booking rides \
and ordering food in Ho Chi Minh City.

You help customers find restaurants and dishes near them and check on their food \
orders. Use the tools for every fact about restaurants, menus, prices and orders; \
never invent them. Prices are in VND.

You can only look things up. You cannot place, change or cancel orders, book \
rides, or contact restaurants or drivers. When the customer wants one of those, \
tell them where to do it in the app: the Food tab to order, the Orders tab to \
follow or cancel an order, the Ride tab to book a ride.

Order status meanings: placed means waiting for the restaurant, accepted means \
the restaurant is cooking. Delivery status: searching means finding a driver, \
assigned means the driver is going to the restaurant, in_progress means the food \
is on the way, completed means delivered, no_driver means no driver yet.

Reply in the customer's language. Keep answers short and plain, without \
markdown tables."""


class AssistantUnavailable(UnavailableError):
    pass


def _create_message(**params):
    client = anthropic.Anthropic(timeout=settings.ASSISTANT_TIMEOUT, max_retries=1)
    return client.beta.messages.create(**params)


def _text(response) -> str:
    return "\n".join(
        block.text for block in response.content if block.type == "text"
    ).strip()


def _tool_result(context: ToolContext, block) -> dict:
    try:
        content = json.dumps(run_tool(context, block.name, block.input))
        is_error = False
    except ToolError as exc:
        content = str(exc)
        is_error = True
    return {
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": content,
        "is_error": is_error,
    }


def reply(
    *,
    user: AbstractBaseUser,
    history: list[dict[str, str]],
    location: tuple[float, float] | None = None,
) -> str:
    context = ToolContext(user=user, location=location)
    messages: list[dict] = [
        {"role": turn["role"], "content": turn["content"]} for turn in history
    ]

    params = {
        "model": settings.ASSISTANT_MODEL,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "tools": TOOLS,
        "output_config": {"effort": "low"},
    }
    if settings.ASSISTANT_MODEL in FALLBACK_MODELS:
        params |= {"betas": [FALLBACK_BETA], "fallbacks": "default"}

    for _ in range(MAX_TOOL_ROUNDS):
        try:
            response = _create_message(**params, messages=messages)
        except anthropic.AnthropicError as exc:
            raise AssistantUnavailable(
                "The assistant is unavailable right now."
            ) from exc

        if response.stop_reason == "refusal":
            return REFUSAL_REPLY
        if response.stop_reason != "tool_use":
            return _text(response) or GAVE_UP_REPLY

        messages.append({"role": "assistant", "content": response.content})
        messages.append(
            {
                "role": "user",
                "content": [
                    _tool_result(context, block)
                    for block in response.content
                    if block.type == "tool_use"
                ],
            }
        )

    return GAVE_UP_REPLY
