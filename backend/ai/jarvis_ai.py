"""JarvisAI — provider-agnostic orchestrator.

Replaces JarvisClaude. The only thing that knows about a specific vendor is
backend/ai/providers/. Business logic (chat router, streaming endpoint, tool
loop) talks to AIProvider through the AIMessage / AITool / AIResponse wire
types.

Responsibilities:
  - Resolve user's provider + API key (BYOAK from UserSettings, fallback env)
  - Resolve tier → model via ai/tiers.py
  - Convert TOOL_SCHEMAS dicts → AITool dataclasses
  - Run the tool-use loop (multi-turn dispatch)
  - Record token usage + cost after each provider call (TokenUsage row)
  - Manage conversation memory + auto-compression
"""
from __future__ import annotations

import logging
import os
from datetime import date as _date
from typing import Optional

from sqlalchemy.orm import Session

import json as _json

from crypto import decrypt
from models import TokenUsage, UserContext, UserSettings

from .exceptions import NoAPIKeyError
from .knowledge import search as knowledge_search
from .memory import ConversationMemory
from .persona import build_system_prompt
from .providers.base import AIMessage, AIResponse, AITool
from .providers.factory import get_provider
from .tiers import TIER_MODELS, estimate_cost, resolve_tier
from .tools import TOOL_SCHEMAS, dispatch

logger = logging.getLogger("jarvis.ai")

MAX_TOOL_TURNS = 8
DEFAULT_PROVIDER = "anthropic"
DEFAULT_TIER = "intelligent"


def _adapt_tools(tool_schemas: list[dict]) -> list[AITool]:
    return [
        AITool(name=t["name"], description=t["description"], input_schema=t["input_schema"])
        for t in tool_schemas
    ]


class JarvisAI:
    def __init__(self, db: Session, user_id: Optional[int] = None):
        self.db = db
        self.user_id = user_id

        # Resolve user settings (may be None for legacy users without a row)
        settings = (
            db.query(UserSettings).filter_by(user_id=user_id).first()
            if user_id is not None
            else None
        )
        self.settings = settings

        provider_name = (settings.ai_provider if settings else None) or DEFAULT_PROVIDER
        tier = (settings.default_model if settings else None) or DEFAULT_TIER

        # Decrypt user's BYOAK key, or fall back to platform env var
        api_key = self._resolve_api_key(provider_name, settings)
        if not api_key:
            raise NoAPIKeyError(provider_name)

        # Build provider client
        self.provider = get_provider(provider_name, api_key)
        self.provider_name = provider_name

        # Resolve tier → model + thinking budget + max tokens
        model_id, thinking_budget, max_tokens = resolve_tier(tier, provider_name)
        self.model = model_id
        self.thinking_budget = thinking_budget
        self.max_tokens = max_tokens
        self.tier = tier

        # Tools + memory
        self.tools = _adapt_tools(TOOL_SCHEMAS)
        self.memory = ConversationMemory(db, user_id)

    # ── Key resolution ──────────────────────────────────────────────────

    @staticmethod
    def _resolve_api_key(provider_name: str, settings: Optional[UserSettings]) -> str:
        # 1) User's BYOAK key (encrypted column)
        if settings is not None:
            field = f"{provider_name}_api_key_encrypted"
            encrypted = getattr(settings, field, None)
            if encrypted:
                try:
                    return decrypt(encrypted) or ""
                except Exception:
                    logger.exception("failed to decrypt %s for user", field)
        # 2) Platform env-var fallback
        return os.getenv(f"{provider_name.upper()}_API_KEY", "").strip()

    # ── Public API ──────────────────────────────────────────────────────

    async def respond(self, user_message: str) -> dict:
        """Send a user message, run any tool loops, return:
            {"text": str, "usage": {input, output, cache_read, cache_write,
                                    thinking, cost_usd, model, provider}}
        Token usage is also persisted to the TokenUsage table."""
        self.memory.append("user", user_message)
        await self.memory.maybe_compress()

        # RAG: fetch relevant chunks before building the system prompt
        knowledge_block = await self._build_knowledge_block(user_message)

        system_text = self._build_system_text(knowledge_block=knowledge_block)
        messages: list[AIMessage] = self._build_message_history()

        # Accumulate usage across all tool-loop turns
        agg = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
            "thinking_tokens": 0,
            "cost_usd": 0.0,
        }

        for _ in range(MAX_TOOL_TURNS):
            resp = await self._call(messages, system_text)
            self._record_usage(resp)
            self._accumulate(agg, resp)

            if resp.tool_calls:
                # Echo assistant turn (with tool calls) back into history
                messages.append(
                    AIMessage(
                        role="assistant",
                        content=self._serialize_tool_use_turn(resp),
                    )
                )
                # Dispatch every tool, collect results
                tool_results_content = []
                for call in resp.tool_calls:
                    result = await dispatch(call.name, call.input, self.db, self.user_id)
                    tool_results_content.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": call.id,
                            "content": str(result)[:8000],
                        }
                    )
                messages.append(AIMessage(role="user", content=tool_results_content))
                continue

            # Final text response
            text = resp.text or "Boss, no response generated."
            self.memory.append("assistant", text)
            return {"text": text, "usage": self._format_usage(agg)}

        fallback = "Boss, I hit my tool limit. Try narrowing the request."
        self.memory.append("assistant", fallback)
        return {"text": fallback, "usage": self._format_usage(agg)}

    # ── Internals ───────────────────────────────────────────────────────

    def _build_system_text(self, knowledge_block: str = "") -> str:
        personality = self.settings.personality_mode if self.settings else None
        s = build_system_prompt(personality)

        # Inject UserContext (about_me, communication style, priorities, team)
        ctx_block = self._build_context_block()
        if ctx_block:
            s += "\n\n" + ctx_block

        # Inject retrieved RAG chunks
        if knowledge_block:
            s += "\n\n" + knowledge_block

        # Inject compressed earlier-conversation summary
        summary = self.memory.summaries()
        if summary:
            s += f"\n\nEarlier-conversation summary:\n{summary}"
        return s

    def _build_context_block(self) -> str:
        if self.user_id is None:
            return ""
        ctx = self.db.query(UserContext).filter_by(user_id=self.user_id).first()
        if not ctx:
            return ""
        parts = []
        if ctx.about_me:
            parts.append(f"About boss: {ctx.about_me}")
        if ctx.communication_style:
            parts.append(f"Communication style: {ctx.communication_style}")
        if ctx.priorities:
            parts.append(f"Top priorities: {ctx.priorities}")
        if ctx.team_members:
            try:
                team = _json.dumps(ctx.team_members)
                parts.append(f"Team: {team}")
            except Exception:
                pass
        if ctx.business_context:
            parts.append(f"Business context: {ctx.business_context}")
        if not parts:
            return ""
        return "USER CONTEXT — USE THIS TO PERSONALIZE ALL RESPONSES:\n" + "\n".join(parts)

    async def _build_knowledge_block(self, query: str) -> str:
        if self.user_id is None:
            return ""
        try:
            chunks = await knowledge_search(self.db, self.user_id, query, limit=5)
        except Exception:
            logger.exception("knowledge search failed")
            return ""
        if not chunks:
            return ""
        body = "\n---\n".join(c.content for c in chunks if c.content)
        return f"RELEVANT KNOWLEDGE FROM USER'S DATA:\n{body}"

    def _build_message_history(self) -> list[AIMessage]:
        return [AIMessage(role=t["role"], content=t["content"]) for t in self.memory.window()]

    def _serialize_tool_use_turn(self, resp: AIResponse) -> list[dict]:
        """Anthropic expects the assistant turn that contained tool_use to be
        replayed verbatim (text blocks + tool_use blocks) before the
        corresponding tool_result blocks. OpenAI uses a different shape but the
        provider abstraction maps it. For now, encode as Anthropic-style and
        let the OpenAI provider's `_flatten_content` handle it."""
        blocks: list[dict] = []
        if resp.text:
            blocks.append({"type": "text", "text": resp.text})
        for call in resp.tool_calls:
            blocks.append(
                {
                    "type": "tool_use",
                    "id": call.id,
                    "name": call.name,
                    "input": call.input,
                }
            )
        return blocks

    async def _call(self, messages: list[AIMessage], system_text: str) -> AIResponse:
        return await self.provider.complete(
            messages=messages,
            system=system_text,
            tools=self.tools,
            model=self.model,
            max_tokens=self.max_tokens,
            thinking_budget=self.thinking_budget,
        )

    def _accumulate(self, agg: dict, resp: AIResponse) -> None:
        agg["input_tokens"] += resp.input_tokens
        agg["output_tokens"] += resp.output_tokens
        agg["cache_read_tokens"] += resp.cache_read_tokens
        agg["cache_write_tokens"] += resp.cache_write_tokens
        agg["thinking_tokens"] += resp.thinking_tokens
        agg["cost_usd"] += estimate_cost(
            provider=self.provider_name,
            tier=self.tier if self.tier in TIER_MODELS else DEFAULT_TIER,
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
        )

    def _format_usage(self, agg: dict) -> dict:
        return {
            "provider": self.provider_name,
            "model": self.model,
            "input": agg["input_tokens"],
            "output": agg["output_tokens"],
            "cache_read": agg["cache_read_tokens"],
            "cache_write": agg["cache_write_tokens"],
            "thinking": agg["thinking_tokens"],
            "cost_usd": round(agg["cost_usd"], 6),
        }

    def _record_usage(self, resp: AIResponse) -> None:
        if self.user_id is None:
            return
        try:
            cost = estimate_cost(
                provider=self.provider_name,
                tier=self.tier if self.tier in TIER_MODELS else DEFAULT_TIER,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
            )
            row = TokenUsage(
                user_id=self.user_id,
                date=_date.today().isoformat(),
                provider=self.provider_name,
                model=self.model,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
                cache_read_tokens=resp.cache_read_tokens,
                cache_write_tokens=resp.cache_write_tokens,
                thinking_tokens=resp.thinking_tokens,
                cost_usd=cost,
            )
            self.db.add(row)
            self.db.commit()
        except Exception:
            logger.exception("failed to record token usage")
            self.db.rollback()
