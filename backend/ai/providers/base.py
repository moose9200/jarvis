"""Provider-agnostic AI interface.

All business logic talks to AIProvider. Concrete implementations live in
sibling files (anthropic_provider.py, openai_provider.py, google_provider.py).
Switching providers is one config flip — no business code touches `anthropic`
or `openai` imports directly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional


# ── Wire types ──────────────────────────────────────────────────────────────


@dataclass
class AIMessage:
    """Single conversation turn. `content` is a string for text-only, or a list
    of content blocks (per Anthropic/OpenAI multimodal schema) for images +
    tool results."""
    role: str           # "user" | "assistant" | "system"
    content: Any        # str | list[dict]


@dataclass
class AITool:
    """Function-calling tool definition. `input_schema` is JSON Schema."""
    name: str
    description: str
    input_schema: dict


@dataclass
class AIToolCall:
    """Normalized tool call requested by the model."""
    id: str
    name: str
    input: dict


@dataclass
class AIResponse:
    """Result of complete(). Token counts use Anthropic naming for clarity;
    OpenAI-style prompt_tokens/completion_tokens are mapped to input/output."""
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    thinking_tokens: int = 0
    thinking: Optional[str] = None
    tool_calls: list[AIToolCall] = field(default_factory=list)
    stop_reason: str = ""        # "end_turn" | "tool_use" | "max_tokens" | ...
    raw: Any = None              # provider-specific response, for debugging


@dataclass
class AIChunk:
    """Single delta from stream(). Frontend renders tokens, handles tool
    pause, and shows final usage on `done`."""
    type: str               # "token" | "thinking" | "tool_call" | "done"
    text: str = ""
    tool_call: Optional[AIToolCall] = None
    usage: Optional[dict] = None    # only on type="done"


# ── Abstract provider ───────────────────────────────────────────────────────


class AIProvider(ABC):
    """Concrete providers wrap a vendor SDK and translate to/from the wire
    types above. They are stateless apart from the API key."""
    name: str = ""

    @abstractmethod
    async def complete(
        self,
        messages: list[AIMessage],
        system: str,
        tools: Optional[list[AITool]],
        model: str,
        max_tokens: int,
        thinking_budget: Optional[int] = None,
    ) -> AIResponse:
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[AIMessage],
        system: str,
        tools: Optional[list[AITool]],
        model: str,
        max_tokens: int,
        thinking_budget: Optional[int] = None,
    ) -> AsyncIterator[AIChunk]:
        ...

    async def validate_key(self) -> bool:
        """Cheap call to verify the API key works. Used by Settings → Test."""
        try:
            r = await self.complete(
                messages=[AIMessage(role="user", content="ping")],
                system="Respond with the single word 'pong'.",
                tools=None,
                model=self.cheapest_model(),
                max_tokens=16,
            )
            return bool(r.text)
        except Exception:
            return False

    def cheapest_model(self) -> str:
        """Override per-provider. Defaults to empty — provider must implement."""
        return ""
