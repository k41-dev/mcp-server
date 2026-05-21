"""
base.py - ModelProvider Abstraktion (Single Source of Truth für alle LLMs)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Protocol, Optional
from pydantic import BaseModel


class ToolCall(BaseModel):
    """Standardisiertes Tool-Call Format (intern)."""
    id: str
    name: str
    arguments: Dict[str, Any]


class ModelProvider(ABC):
    """Abstract Base Class für alle LLM-Provider."""

    name: str
    supports_streaming: bool = True
    supports_tool_calling: bool = True

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Einheitliche Chat-Schnittstelle. Muss von jedem Provider implementiert werden."""
        pass

    def convert_tools(self, tools: List[Dict]) -> List[Dict]:
        """Default: OpenAI-kompatibles Format. Kann von Providern überschrieben werden."""
        return tools

    def parse_tool_calls(self, response: Any) -> List[ToolCall]:
        """Standard-Parsing. Wird von Ollama/Claude/Gemini angepasst."""
        return []


# Globale Registry (wird in __init__.py gefüllt)
_providers: Dict[str, ModelProvider] = {}


def register_provider(provider: ModelProvider) -> None:
    _providers[provider.name.lower()] = provider


def get_provider(name: str) -> Optional[ModelProvider]:
    return _providers.get(name.lower())