import os
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from anthropic import Anthropic

from .persona import SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS, dispatch
from .memory import ConversationMemory

MODEL = "claude-sonnet-4-6"
MAX_TOOL_TURNS = 8


class JarvisClaude:
    def __init__(self, db: Session):
        self.db = db
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        self.memory = ConversationMemory(db)

    async def respond(self, user_message: str) -> str:
        self.memory.append("user", user_message)
        await self.memory.maybe_compress()
        summary = self.memory.summaries()
        system_blocks: List[Dict[str, Any]] = [
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        if summary:
            system_blocks.append({
                "type": "text",
                "text": f"Earlier-conversation summary:\n{summary}",
            })

        messages: List[Dict[str, Any]] = []
        for t in self.memory.window():
            messages.append({"role": t["role"], "content": t["content"]})

        cached_tools = [
            {**tool, "cache_control": {"type": "ephemeral"}} if i == len(TOOL_SCHEMAS) - 1 else tool
            for i, tool in enumerate(TOOL_SCHEMAS)
        ]

        for _ in range(MAX_TOOL_TURNS):
            resp = self.client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system_blocks,
                tools=cached_tools,
                messages=messages,
            )
            if resp.stop_reason == "tool_use":
                assistant_blocks = []
                tool_results = []
                for block in resp.content:
                    if block.type == "tool_use":
                        result = await dispatch(block.name, block.input or {}, self.db)
                        assistant_blocks.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result)[:8000],
                        })
                    elif block.type == "text":
                        assistant_blocks.append({"type": "text", "text": block.text})
                messages.append({"role": "assistant", "content": assistant_blocks})
                messages.append({"role": "user", "content": tool_results})
                continue

            text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
            self.memory.append("assistant", text)
            return text

        fallback = "Boss, I hit my tool limit. Try narrowing the request."
        self.memory.append("assistant", fallback)
        return fallback
