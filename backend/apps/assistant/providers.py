import json
from dataclasses import dataclass, field
from typing import Any

import anthropic
import openai
from django.conf import settings

MAX_TOKENS = 4096
FALLBACK_BETA = "server-side-fallback-2026-07-01"
FALLBACK_MODELS = {
    "claude-fable-5-1",
    "claude-opus-5-5",
    "claude-opus-5",
    "claude-sonnet-5-5",
}


class ProviderError(Exception):
    pass


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: Any


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    content: str
    is_error: bool


@dataclass(frozen=True)
class Turn:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    refused: bool = False
    raw: Any = None


def _create_message(**params):
    client = anthropic.Anthropic(timeout=settings.ASSISTANT_TIMEOUT, max_retries=1)
    return client.beta.messages.create(**params)


def _create_completion(**params):
    client = openai.OpenAI(
        api_key=settings.ASSISTANT_API_KEY,
        base_url=settings.ASSISTANT_BASE_URL,
        timeout=settings.ASSISTANT_TIMEOUT,
        max_retries=1,
    )
    return client.chat.completions.create(**params)


class AnthropicProvider:
    def __init__(self, *, model: str, system: str, tools: list[dict]):
        self.params = {
            "model": model,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "tools": tools,
            "output_config": {"effort": "low"},
        }
        if model in FALLBACK_MODELS:
            self.params |= {"betas": [FALLBACK_BETA], "fallbacks": "default"}

    def complete(self, messages: list[dict]) -> Turn:
        try:
            response = _create_message(**self.params, messages=messages)
        except anthropic.AnthropicError as exc:
            raise ProviderError(str(exc)) from exc

        text = "\n".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
        calls = []
        if response.stop_reason == "tool_use":
            calls = [
                ToolCall(id=block.id, name=block.name, arguments=block.input)
                for block in response.content
                if block.type == "tool_use"
            ]
        return Turn(
            text=text,
            tool_calls=calls,
            refused=response.stop_reason == "refusal",
            raw=response.content,
        )

    def add_turn(
        self, messages: list[dict], turn: Turn, results: list[ToolResult]
    ) -> None:
        messages.append({"role": "assistant", "content": turn.raw})
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": result.call_id,
                        "content": result.content,
                        "is_error": result.is_error,
                    }
                    for result in results
                ],
            }
        )


def _parse_arguments(raw: str | None) -> Any:
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return None


class OpenAIProvider:
    def __init__(self, *, model: str, system: str, tools: list[dict]):
        self.model = model
        self.system = system
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            }
            for tool in tools
        ]

    def complete(self, messages: list[dict]) -> Turn:
        if not settings.ASSISTANT_API_KEY:
            raise ProviderError("ASSISTANT_API_KEY is not set.")
        try:
            response = _create_completion(
                model=self.model,
                max_tokens=MAX_TOKENS,
                tools=self.tools,
                messages=[{"role": "system", "content": self.system}, *messages],
            )
        except openai.OpenAIError as exc:
            raise ProviderError(str(exc)) from exc
        if not response.choices:
            raise ProviderError("The model returned no choices.")

        choice = response.choices[0]
        message = choice.message
        calls = [
            ToolCall(
                id=call.id,
                name=call.function.name,
                arguments=_parse_arguments(call.function.arguments),
            )
            for call in message.tool_calls or []
        ]
        return Turn(
            text=(message.content or "").strip(),
            tool_calls=calls,
            refused=choice.finish_reason == "content_filter" or bool(message.refusal),
            raw=message,
        )

    def add_turn(
        self, messages: list[dict], turn: Turn, results: list[ToolResult]
    ) -> None:
        messages.append(
            {
                "role": "assistant",
                "content": turn.raw.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in turn.raw.tool_calls
                ],
            }
        )
        for result in results:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": result.call_id,
                    "content": f"Error: {result.content}"
                    if result.is_error
                    else result.content,
                }
            )


PROVIDERS = {"anthropic": AnthropicProvider, "openai": OpenAIProvider}
