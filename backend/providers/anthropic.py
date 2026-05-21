"""
anthropic.py - Anthropic (Claude) Provider mit Tool-Calling-Unterstützung
"""

import asyncio
from typing import List, Dict, Any, Optional
from backend.config import settings
from .base import ModelProvider, register_provider


class AnthropicProvider(ModelProvider):
    name = "anthropic"
    supports_tool_calling = True

    # === Attribute aus base.py ===
    streaming_type = "anthropic"
    default_model = settings.ANTHROPIC_MODEL

    def __init__(self):
        self.client = None

    def _get_client(self):
        if self.client is None:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            except ImportError:
                raise RuntimeError(
                    "anthropic package not installed. "
                    "Run: pip install anthropic"
                )
        return self.client

    def _convert_tools_to_anthropic(self, tools: Optional[List[Dict]]) -> Optional[List[Dict]]:
        """Konvertiert unser Tool-Format in Anthropics Format."""
        if not tools:
            return None

        anthropic_tools = []
        for tool in tools:
            fn = tool.get("function", {})
            anthropic_tools.append({
                "name": fn.get("name"),
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {})
            })
        return anthropic_tools

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 4096,
        stream: bool = False,
    ) -> Dict[str, Any] | Any:

        client = self._get_client()
        model = self.default_model

        # Anthropic erwartet Messages ohne System-Rolle im Array
        # System-Prompt wird separat übergeben
        system_prompt = None
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        anthropic_tools = self._convert_tools_to_anthropic(tools)

        try:
            if stream:
                # === STREAMING ===
                # Hinweis: Vollständiges Tool-Calling-Streaming ist bei Anthropic komplex.
                # Hier erstmal Text-Streaming.
                stream_response = await asyncio.to_thread(
                    client.messages.create,
                    model=model,
                    max_tokens=max_tokens or 4096,
                    messages=anthropic_messages,
                    system=system_prompt,
                    tools=anthropic_tools,
                    temperature=temperature,
                    stream=True
                )
                return stream_response

            else:
                # === NON-STREAMING mit Tool-Calling ===
                response = await asyncio.to_thread(
                    client.messages.create,
                    model=model,
                    max_tokens=max_tokens or 4096,
                    messages=anthropic_messages,
                    system=system_prompt,
                    tools=anthropic_tools,
                    temperature=temperature
                )

                # Inhalt extrahieren
                content_blocks = response.content
                text_content = ""
                tool_calls = []

                for block in content_blocks:
                    if block.type == "text":
                        text_content += block.text
                    elif block.type == "tool_use":
                        tool_calls.append({
                            "id": block.id,
                            "type": "function",
                            "function": {
                                "name": block.name,
                                "arguments": block.input
                            }
                        })

                return {
                    "content": text_content,
                    "tool_calls": tool_calls if tool_calls else None,
                    "raw": response.model_dump()
                }

        except Exception as e:
            return {
                "content": f"Anthropic Error: {str(e)}",
                "tool_calls": None,
                "error": True
            }


# Automatisch registrieren
anthropic_provider = AnthropicProvider()
register_provider(anthropic_provider)