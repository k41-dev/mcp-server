"""
grok.py - xAI Grok Provider (OpenAI-kompatibel) – korrigiert
"""

from typing import List, Dict, Any, Optional
from backend.config import settings
from .base import ModelProvider, register_provider


class GrokProvider(ModelProvider):
    name = "grok"
    supports_tool_calling = True

    def __init__(self):
        self.client = None

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Dict[str, Any] | Any:
        if self.client is None:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=settings.XAI_API_KEY,
                base_url="https://api.x.ai/v1"
            ) if settings.XAI_API_KEY else None

        if not self.client:
            raise RuntimeError("XAI_API_KEY not configured")

        import asyncio

        if stream:
            # Streaming-Pfad
            stream_response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=settings.XAI_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto" if tools else None,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            return stream_response   # Gibt den OpenAI-Stream-Iterator zurück

        else:
            # Non-Streaming-Pfad (wie bisher)
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=settings.XAI_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto" if tools else None,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )

            msg = response.choices[0].message

            tool_calls = None
            if msg.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in msg.tool_calls
                ]

            return {
                "content": msg.content or "",
                "tool_calls": tool_calls,
                "raw": response.model_dump()
            }


# Automatisch registrieren
grok_provider = GrokProvider()
register_provider(grok_provider)