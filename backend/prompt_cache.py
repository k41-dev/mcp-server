#!/usr/bin/env python3
"""
prompt_cache.py - Einfacher, event-gesteuerter Prompt-Cache

Cacht den dynamisch gebauten System-Prompt basierend auf der Version.
Wird bei Persona- oder Skill-Änderungen automatisch invalidiert.
"""

import logging
from typing import Optional, Dict

from backend.events import subscribe, EventTypes

logger = logging.getLogger("mcp.prompt_cache")

_cache: Dict[str, str] = {}


def get_cached_prompt(version: str) -> Optional[str]:
    """Gibt den gecachten Prompt zurück, falls vorhanden."""
    return _cache.get(version)


def set_cached_prompt(version: str, prompt: str) -> None:
    """Speichert den Prompt im Cache."""
    _cache[version] = prompt
    logger.debug(f"Prompt gecached (Version: {version})")


def clear_cache() -> None:
    """Leert den gesamten Cache (z. B. bei State-Change)."""
    global _cache
    _cache = {}
    logger.info("🧹 Prompt-Cache wurde invalidiert")


# === Automatische Invalidierung bei State-Changes ===
def _on_context_changed(data: dict) -> None:
    clear_cache()


subscribe(EventTypes.PERSONA_ACTIVATED, _on_context_changed)
subscribe(EventTypes.SKILL_ACTIVATED, _on_context_changed)
subscribe(EventTypes.CONTEXT_CLEARED, _on_context_changed)
subscribe(EventTypes.MODEL_CHANGED, _on_context_changed)

logger.info("✅ Prompt-Cache mit Event-Invalidierung initialisiert")