import os
import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from openai import AsyncOpenAI

from .persona import SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS, dispatch
from .memory import ConversationMemory

# Use GROQ_API_KEY if set, else fall back to Anthropic-compatible via openai client
GROQ_BASE = "https://api.groq.com/openai/v1"
MODEL = os.getenv("AI_MODEL", "llama-3.3-70b-versatile")
MAX_TOOL_TURNS = 8


def _openai_tools(schemas):
    """Convert Anthropic-style tool schemas to OpenAI function format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        }
        for t in schemas
    ]


class JarvisClaude:
    def __init__(self, db: Session):
        self.db = db
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "")
        base_url = GROQ_BASE if os.getenv("GROQ_API_KEY") else None
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.memory = ConversationMemory(db)

    async def respond(self, user_message: str) -> str:
        self.memory.append("user", user_message)
        await self.memory.maybe_compress()
        summary = self.memory.summaries()

        system_text = SYSTEM_PROMPT
        if summary:
            system_text += f"\n\nEarlier-conversation summary:\n{summary}"

        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_text}]
        for t in self.memory.window():
            messages.append({"role": t["role"], "content": t["content"]})

        tools = _openai_tools(TOOL_SCHEMAS)

        for _ in range(MAX_TOOL_TURNS):
            resp = await self.client.chat.completions.create(
                model=MODEL,
                max_tokens=1024,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            choice = resp.choices[0]
            msg = choice.message

            if choice.finish_reason == "tool_calls" and msg.tool_calls:
                # Append assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in msg.tool_calls
                    ],
                })
                # Dispatch each tool and append results
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except Exception:
                        args = {}
                    result = await dispatch(tc.function.name, args, self.db)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(result)[:8000],
                    })
                continue

            text = msg.content or "Boss, no response generated."
            self.memory.append("assistant", text)
            return text

        fallback = "Boss, I hit my tool limit. Try narrowing the request."
        self.memory.append("assistant", fallback)
        return fallback
