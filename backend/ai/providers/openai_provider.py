"""OpenAI-compatible provider.

Single class that handles:
  - OpenAI (api.openai.com)
  - Groq (api.groq.com/openai/v1)
  - Mistral (api.mistral.ai/v1)
  - Any other Chat-Completions-compatible endpoint

Distinguished from each other only by base_url + name. The shape of the
messages/tools API is identical.
"""
from __future__ import annotations

import json
from typing import AsyncIterator, Optional

from openai import AsyncOpenAI

from .base import (
    AIChunk,
    AIMessage,
    AIProvider,
    AIResponse,
    AITool,
    AIToolCall,
)


class OpenAICompatibleProvider(AIProvider):
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        provider_name: str = "openai",
        cheap_model: str = "gpt-4o-mini",
    ):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.name = provider_name
        self._cheap_model = cheap_model

    def cheapest_model(self) -> str:
        return self._cheap_model

    # ── Internal helpers ────────────────────────────────────────────────

    def _msgs(self, messages: list[AIMessage], system: str) -> list[dict]:
        result: list[dict] = []
        if system:
            result.append({"role": "system", "content": system})
        for m in messages:
            content = m.content
            if isinstance(content, list):
                content = self._flatten_content(content)
            result.append({"role": m.role, "content": content})
        return result

    def _flatten_content(self, content: list[dict]) -> list[dict]:
        """Translate Anthropic-style content blocks → OpenAI multimodal format."""
        out: list[dict] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            t = item.get("type")
            if t == "text":
                out.append({"type": "text", "text": item.get("text", "")})
            elif t == "image":
                src = item.get("source", {})
                url = src.get("url") or src.get("data") or ""
                out.append({"type": "image_url", "image_url": {"url": url}})
            elif t == "tool_result":
                # OpenAI tool_results go via a separate role; for safety,
                # serialize as text fallback if it leaks into a normal content block.
                out.append({"type": "text", "text": str(item.get("content", ""))})
        return out

    def _tools(self, tools: Optional[list[AITool]]) -> Optional[list[dict]]:
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in tools
        ]

    # ── Public API ──────────────────────────────────────────────────────

    async def complete(
        self,
        messages: list[AIMessage],
        system: str,
        tools: Optional[list[AITool]],
        model: str,
        max_tokens: int,
        thinking_budget: Optional[int] = None,  # ignored — OpenAI handles reasoning internally
    ) -> AIResponse:
        kwargs: dict = dict(
            model=model,
            max_tokens=max_tokens,
            messages=self._msgs(messages, system),
        )
        tool_defs = self._tools(tools)
        if tool_defs:
            kwargs["tools"] = tool_defs

        resp = await self.client.chat.completions.create(**kwargs)

        msg = resp.choices[0].message
        tool_calls: list[AIToolCall] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    parsed = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    parsed = {}
                tool_calls.append(AIToolCall(id=tc.id, name=tc.function.name, input=parsed))

        usage = resp.usage
        return AIResponse(
            text=msg.content or "",
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            tool_calls=tool_calls,
            stop_reason=resp.choices[0].finish_reason or "",
            raw=resp,
        )

    async def stream(
        self,
        messages: list[AIMessage],
        system: str,
        tools: Optional[list[AITool]],
        model: str,
        max_tokens: int,
        thinking_budget: Optional[int] = None,
    ) -> AsyncIterator[AIChunk]:
        kwargs: dict = dict(
            model=model,
            max_tokens=max_tokens,
            messages=self._msgs(messages, system),
            stream=True,
            stream_options={"include_usage": True},
        )
        tool_defs = self._tools(tools)
        if tool_defs:
            kwargs["tools"] = tool_defs

        stream = await self.client.chat.completions.create(**kwargs)
        total_in = total_out = 0
        async for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield AIChunk(type="token", text=delta.content)
            if chunk.usage:
                total_in = chunk.usage.prompt_tokens or 0
                total_out = chunk.usage.completion_tokens or 0
        yield AIChunk(
            type="done",
            usage={"input": total_in, "output": total_out, "cache_read": 0, "cache_write": 0},
        )
