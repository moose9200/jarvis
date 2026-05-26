"""Anthropic Claude provider.

Features used:
  - Prompt caching on the system prompt (cache_control: ephemeral) to slash
    cost on repeated requests with the same system prompt.
  - Extended thinking via the `thinking` param (Claude Sonnet 4.5+ and Opus).
  - Tool use loop (single-shot — caller orchestrates multi-turn tool calls
    using the returned tool_calls list).
"""
from __future__ import annotations

from typing import AsyncIterator, Optional

import anthropic

from .base import (
    AIChunk,
    AIMessage,
    AIProvider,
    AIResponse,
    AITool,
    AIToolCall,
)


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, api_key: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    def cheapest_model(self) -> str:
        return "claude-haiku-4-5"

    # ── Internal helpers ────────────────────────────────────────────────

    def _msgs(self, messages: list[AIMessage]) -> list[dict]:
        # Skip system messages — those go to the top-level `system` param.
        return [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

    def _tools(self, tools: Optional[list[AITool]]) -> list[dict]:
        if not tools:
            return []
        return [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in tools
        ]

    def _system_block(self, system: str) -> list[dict]:
        # Cache the system prompt — huge cost win on chatty sessions.
        return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

    # ── Public API ──────────────────────────────────────────────────────

    async def complete(
        self,
        messages: list[AIMessage],
        system: str,
        tools: Optional[list[AITool]],
        model: str,
        max_tokens: int,
        thinking_budget: Optional[int] = None,
    ) -> AIResponse:
        kwargs: dict = dict(
            model=model,
            max_tokens=max_tokens,
            messages=self._msgs(messages),
            system=self._system_block(system),
        )
        tool_defs = self._tools(tools)
        if tool_defs:
            kwargs["tools"] = tool_defs
        if thinking_budget:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

        resp = await self.client.messages.create(**kwargs)

        text_parts: list[str] = []
        thinking_parts: list[str] = []
        tool_calls: list[AIToolCall] = []
        for block in resp.content:
            btype = getattr(block, "type", "")
            if btype == "text":
                text_parts.append(block.text)
            elif btype == "thinking":
                thinking_parts.append(getattr(block, "thinking", "") or "")
            elif btype == "tool_use":
                tool_calls.append(
                    AIToolCall(id=block.id, name=block.name, input=block.input or {})
                )

        usage = resp.usage
        return AIResponse(
            text="".join(text_parts),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            thinking="\n".join(thinking_parts) if thinking_parts else None,
            tool_calls=tool_calls,
            stop_reason=resp.stop_reason or "",
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
            messages=self._msgs(messages),
            system=self._system_block(system),
        )
        tool_defs = self._tools(tools)
        if tool_defs:
            kwargs["tools"] = tool_defs
        if thinking_budget:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield AIChunk(type="token", text=text)
            final = await stream.get_final_message()

            # Emit tool_use blocks (if any) so the orchestrator can dispatch.
            tool_calls: list[AIToolCall] = []
            for block in final.content:
                if getattr(block, "type", "") == "tool_use":
                    tc = AIToolCall(id=block.id, name=block.name, input=block.input or {})
                    tool_calls.append(tc)
                    yield AIChunk(type="tool_call", tool_call=tc)

            yield AIChunk(
                type="done",
                usage={
                    "input": final.usage.input_tokens,
                    "output": final.usage.output_tokens,
                    "cache_read": getattr(final.usage, "cache_read_input_tokens", 0) or 0,
                    "cache_write": getattr(final.usage, "cache_creation_input_tokens", 0) or 0,
                    "stop_reason": final.stop_reason or "",
                    # Replay payload: orchestrator needs the assistant turn
                    # (text + tool_use blocks) verbatim before tool_result turns.
                    "_assistant_blocks": [
                        {"type": "text", "text": b.text} if getattr(b, "type", "") == "text"
                        else {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input or {}}
                        for b in final.content
                        if getattr(b, "type", "") in ("text", "tool_use")
                    ],
                },
            )
