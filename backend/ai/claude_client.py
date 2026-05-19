import os
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import anthropic

from .persona import SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS, dispatch
from .memory import ConversationMemory

MODEL = os.getenv("AI_MODEL", "claude-sonnet-4-5")
MAX_TOOL_TURNS = 8


class JarvisClaude:
    def __init__(self, db: Session, user_id: Optional[int] = None):
        self.db = db
        self.user_id = user_id
        self.client = anthropic.AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY", "")
        )
        self.memory = ConversationMemory(db, user_id)

    async def respond(self, user_message: str) -> str:
        self.memory.append("user", user_message)
        await self.memory.maybe_compress()
        summary = self.memory.summaries()

        system_text = SYSTEM_PROMPT
        if summary:
            system_text += f"\n\nEarlier-conversation summary:\n{summary}"

        messages: List[Dict[str, Any]] = []
        for t in self.memory.window():
            messages.append({"role": t["role"], "content": t["content"]})

        for _ in range(MAX_TOOL_TURNS):
            resp = await self.client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system_text,
                messages=messages,
                tools=TOOL_SCHEMAS,
            )

            if resp.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": resp.content})

                tool_results = []
                for block in resp.content:
                    if block.type == "tool_use":
                        result = await dispatch(block.name, block.input, self.db, self.user_id)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result)[:8000],
                        })

                messages.append({"role": "user", "content": tool_results})
                continue

            text = ""
            for block in resp.content:
                if hasattr(block, "text"):
                    text += block.text
            text = text or "Boss, no response generated."
            self.memory.append("assistant", text)
            return text

        fallback = "Boss, I hit my tool limit. Try narrowing the request."
        self.memory.append("assistant", fallback)
        return fallback
