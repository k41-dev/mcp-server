"""
grok.py - xAI Grok Provider (OpenAI-kompatibel)
"""

from openai import OpenAI
from typing import List, Dict, Any, Optional
from backend.config import settings
from .base import ModelProvider, ToolCall, register_provider


class GrokProvider(ModelProvider):
    name = "grok"
    supports_tool_calling = True

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.XAI_API_KEY,
            base_url="https://api.x.ai/v1"
        ) if settings.XAI_API_KEY else None

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("XAI_API_KEY not configured")

        response = self.client.chat.completions.create(
            model=settings.XAI_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
        )

        # Für nicht-streaming (aktueller Use-Case)
        if not stream:
            msg = response.choices[0].message
            return {
                "content": msg.content or "",
                "tool_calls": msg.tool_calls,
                "raw": response.model_dump()
            }
        return {"content": "", "tool_calls": None, "raw": response}  # Stream-Handling kommt später


# Automatisch registrieren
grok_provider = GrokProvider()
register_provider(grok_provider)