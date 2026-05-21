"""
base.py - ModelProvider Abstraktion (Single Source of Truth für alle LLMs)
"""

from abc import ABC
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel


class ToolCall(BaseModel):
    """Standardisiertes Tool-Call Format (intern)."""
    id: str
    name: str
    arguments: Dict[str, Any]


# === Streaming-Typ für bessere Abstraktion ===
StreamingType = Literal["openai", "ollama", "anthropic", "google"]


class ModelProvider(ABC):
    """
    Abstract Base Class für alle LLM-Provider.

    Wichtige Design-Entscheidungen:
    - Jeder Provider deklariert seine Fähigkeiten explizit.
    - Streaming wird über `streaming_type` klassifiziert, damit
      der Server die Antwort korrekt handhaben kann.
    """

    name: str
    supports_streaming: bool = True
    supports_tool_calling: bool = True

    streaming_type: StreamingType = "openai"
    default_model: Optional[str] = None

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Dict[str, Any] | Any:
        """
        Führt eine Chat-Anfrage durch.
        Bei stream=True gibt der Provider einen Stream-Iterator zurück.
        Der genaue Typ hängt von `streaming_type` ab.
        """
        raise NotImplementedError(f"Provider '{self.name}' hat chat() nicht implementiert.")

    def convert_tools(self, tools: List[Dict]) -> List[Dict]:
        """
        Optional: Provider-spezifische Konvertierung der Tool-Definitionen.
        Die meisten Provider (OpenAI-kompatibel) brauchen das nicht.
        """
        return tools

    def parse_tool_calls(self, response: Any) -> List[ToolCall]:
        """
        Optional: Extrahiert Tool-Calls aus der rohen Provider-Antwort.
        Wird aktuell nur bei Ollama als Fallback genutzt.
        """
        return []


# Globale Registry (wird in __init__.py gefüllt)
_providers: Dict[str, ModelProvider] = {}


def register_provider(provider: ModelProvider) -> None:
    _providers[provider.name.lower()] = provider


def get_provider(name: str) -> Optional[ModelProvider]:
    return _providers.get(name.lower())