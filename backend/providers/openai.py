"""
openai.py - OpenAI Provider (GPT-4o, o1 etc.)
"""

from typing import List, Dict, Any, Optional
from backend.config import settings
from .base import ModelProvider, register_provider


class OpenAIProvider(ModelProvider):
    name = "openai"
    supports_tool_calling = True

    # === NEU: Vererbte Attribute aus base.py ===
    streaming_type = "openai"
    default_model = settings.OPENAI_MODEL

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
                api_key=settings.OPENAI_API_KEY
            ) if settings.OPENAI_API_KEY else None

        if not self.client:
            raise RuntimeError("OPENAI_API_KEY not configured")

        import asyncio

        # Nutze das deklarierte Default-Modell
        model = self.default_model

        if stream:
            stream_response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto" if tools else None,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            return stream_response
        else:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=model,
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
openai_provider = OpenAIProvider()
register_provider(openai_provider)