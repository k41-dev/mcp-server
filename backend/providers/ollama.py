"""
ollama.py - Lokaler Ollama Provider mit defensivem Tool-Calling
"""

import ollama
import json
from typing import List, Dict, Any, Optional
from backend.config import settings
from .base import ModelProvider, ToolCall, register_provider


class OllamaProvider(ModelProvider):
    name = "ollama"
    supports_tool_calling = True

    def __init__(self):
        self.client = ollama.Client(host=settings.OLLAMA_URL)
        self.model = settings.OLLAMA_MODEL

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        resp = self.client.chat(
            model=self.model,
            messages=messages,
            tools=tools,
            stream=stream
        )

        message_obj = resp.get("message", {}) if not stream else {}
        content = message_obj.get("content", "") or ""
        tool_calls = message_obj.get("tool_calls", []) or []

        # === Raw-JSON Fallback (wie bisher in chat_handler.py) ===
        if not tool_calls and isinstance(content, str) and content.strip().startswith("{"):
            try:
                parsed = json.loads(content.strip())
                if isinstance(parsed, dict) and parsed.get("name"):
                    tool_calls = [{
                        "function": {
                            "name": parsed.get("name"),
                            "arguments": parsed.get("parameters") or parsed.get("arguments") or {}
                        }
                    }]
                    content = ""
            except:
                pass

        return {
            "content": content,
            "tool_calls": tool_calls,
            "raw": resp
        }


# Automatisch registrieren
ollama_provider = OllamaProvider()
register_provider(ollama_provider)