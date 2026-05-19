"""Google Gemini provider via google-generativeai.

Loaded lazily — if `google-generativeai` isn't installed, the factory falls
back to raising ValueError on `get_provider("google", ...)` rather than
crashing import for everyone.
"""
from __future__ import annotations

import json
from typing import AsyncIterator, Optional

from .base import (
    AIChunk,
    AIMessage,
    AIProvider,
    AIResponse,
    AITool,
    AIToolCall,
)


class GoogleProvider(AIProvider):
    name = "google"

    def __init__(self, api_key: str):
        try:
            import google.generativeai as genai
        except ImportError as e:
            raise RuntimeError(
                "google-generativeai not installed. Add it to requirements.txt to use Gemini."
            ) from e
        self._genai = genai
        genai.configure(api_key=api_key)

    def cheapest_model(self) -> str:
        return "gemini-2.5-flash-lite"

    # ── Internal helpers ────────────────────────────────────────────────

    def _to_gemini_role(self, role: str) -> str:
        # Gemini uses "user" and "model" (not "assistant").
        return "model" if role == "assistant" else "user"

    def _to_gemini_messages(self, messages: list[AIMessage]) -> list[dict]:
        out = []
        for m in messages:
            if m.role == "system":
                continue
            parts = m.content if isinstance(m.content, list) else [{"text": str(m.content)}]
            # Normalize to Gemini Parts shape
            norm_parts = []
            for p in parts:
                if isinstance(p, str):
                    norm_parts.append({"text": p})
                elif isinstance(p, dict):
                    if p.get("type") == "text":
                        norm_parts.append({"text": p.get("text", "")})
                    elif p.get("type") == "image":
                        url = p.get("source", {}).get("url", "")
                        if url:
                            norm_parts.append({"file_data": {"mime_type": "image/png", "file_uri": url}})
            out.append({"role": self._to_gemini_role(m.role), "parts": norm_parts})
        return out

    def _to_gemini_tools(self, tools: Optional[list[AITool]]):
        if not tools:
            return None
        return [{
            "function_declarations": [
                {"name": t.name, "description": t.description, "parameters": t.input_schema}
                for t in tools
            ]
        }]

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
        gen_model = self._genai.GenerativeModel(
            model_name=model,
            system_instruction=system or None,
            tools=self._to_gemini_tools(tools),
        )
        resp = await gen_model.generate_content_async(
            self._to_gemini_messages(messages),
            generation_config={"max_output_tokens": max_tokens},
        )
        text_parts: list[str] = []
        tool_calls: list[AIToolCall] = []
        for cand in resp.candidates or []:
            for part in (cand.content.parts if cand.content else []):
                if hasattr(part, "text") and part.text:
                    text_parts.append(part.text)
                fc = getattr(part, "function_call", None)
                if fc and fc.name:
                    args = dict(fc.args) if fc.args else {}
                    tool_calls.append(
                        AIToolCall(id=f"call_{fc.name}", name=fc.name, input=args)
                    )

        usage = getattr(resp, "usage_metadata", None)
        return AIResponse(
            text="".join(text_parts),
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            cache_read_tokens=getattr(usage, "cached_content_token_count", 0) or 0,
            tool_calls=tool_calls,
            stop_reason="end_turn",
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
        gen_model = self._genai.GenerativeModel(
            model_name=model,
            system_instruction=system or None,
            tools=self._to_gemini_tools(tools),
        )
        stream = await gen_model.generate_content_async(
            self._to_gemini_messages(messages),
            generation_config={"max_output_tokens": max_tokens},
            stream=True,
        )
        total_in = total_out = 0
        async for chunk in stream:
            if hasattr(chunk, "text") and chunk.text:
                yield AIChunk(type="token", text=chunk.text)
            usage = getattr(chunk, "usage_metadata", None)
            if usage:
                total_in = getattr(usage, "prompt_token_count", 0) or 0
                total_out = getattr(usage, "candidates_token_count", 0) or 0
        yield AIChunk(
            type="done",
            usage={"input": total_in, "output": total_out, "cache_read": 0, "cache_write": 0},
        )
