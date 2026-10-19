import json

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ImproperlyConfigured

from apps.assistant.providers import PROVIDERS, ProviderError, ToolCall, ToolResult
from apps.assistant.tools import TOOLS, ToolContext, ToolError, run_tool
from apps.shared.exceptions import UnavailableError

MAX_TOOL_ROUNDS = 5
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


def _provider():
    provider = PROVIDERS.get(settings.ASSISTANT_PROVIDER)
    if provider is None:
        raise ImproperlyConfigured(
            f"Unknown ASSISTANT_PROVIDER {settings.ASSISTANT_PROVIDER!r}."
        )
    return provider(model=settings.ASSISTANT_MODEL, system=SYSTEM_PROMPT, tools=TOOLS)


def _run(context: ToolContext, call: ToolCall) -> ToolResult:
    try:
        content = json.dumps(run_tool(context, call.name, call.arguments))
        return ToolResult(call_id=call.id, content=content, is_error=False)
    except ToolError as exc:
        return ToolResult(call_id=call.id, content=str(exc), is_error=True)


def reply(
    *,
    user: AbstractBaseUser,
    history: list[dict[str, str]],
    location: tuple[float, float] | None = None,
) -> str:
    provider = _provider()
    context = ToolContext(user=user, location=location)
    messages: list[dict] = [
        {"role": turn["role"], "content": turn["content"]} for turn in history
    ]

    for _ in range(MAX_TOOL_ROUNDS):
        try:
            turn = provider.complete(messages)
        except ProviderError as exc:
            raise AssistantUnavailable(
                "The assistant is unavailable right now."
            ) from exc

        if turn.refused:
            return REFUSAL_REPLY
        if not turn.tool_calls:
            return turn.text or GAVE_UP_REPLY

        results = [_run(context, call) for call in turn.tool_calls]
        provider.add_turn(messages, turn, results)

    return GAVE_UP_REPLY
