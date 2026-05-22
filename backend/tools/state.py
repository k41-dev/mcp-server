#!/usr/bin/env python3
"""
state.py - Zentraler, beobachtbarer Manager für transiente Sitzungszustände
           (active persona, active skill). Single Source of Truth.
"""

from typing import Dict, Any, Optional
from backend.memory import DEFAULT_SESSION_ID
from backend.events import publish, EventTypes
from backend.config import settings


# ====================== STATES ======================
_active_persona: Dict[int, Dict[str, Any]] = {}
_active_skill: Dict[int, Dict[str, Any]] = {}
_active_provider: Dict[int, str] = {}


# ====================== ACTIVE PERSONA ======================
def set_active_persona(persona_name: str, instructions: str, intensity: int = 7) -> None:
    _active_persona[DEFAULT_SESSION_ID] = {
        "name": persona_name.lower().strip(),
        "instructions": instructions.strip(),
        "intensity": max(1, min(10, intensity)),
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
    }
    publish(EventTypes.PERSONA_ACTIVATED, {
        "persona_name": persona_name.lower().strip(),
        "intensity": intensity
    })


def get_active_persona() -> Optional[Dict[str, Any]]:
    return _active_persona.get(DEFAULT_SESSION_ID)


def clear_active_persona() -> None:
    _active_persona.pop(DEFAULT_SESSION_ID, None)
    publish(EventTypes.CONTEXT_CLEARED, {"cleared": "persona"})


# ====================== ACTIVE SKILL ======================
def set_active_skill(skill_name: str, content: str) -> None:
    _active_skill[DEFAULT_SESSION_ID] = {
        "name": skill_name.lower().strip(),
        "content": content.strip(),
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
    }
    publish(EventTypes.SKILL_ACTIVATED, {
        "skill_name": skill_name.lower().strip()
    })


def get_active_skill() -> Optional[Dict[str, Any]]:
    return _active_skill.get(DEFAULT_SESSION_ID)


def clear_active_skill() -> None:
    _active_skill.pop(DEFAULT_SESSION_ID, None)
    publish(EventTypes.CONTEXT_CLEARED, {"cleared": "skill"})


# ====================== ACTIVE PROVIDER ======================
def set_active_provider(provider: str) -> None:
    provider = provider.lower().strip()
    if provider not in ("grok", "ollama", "openai", "anthropic"):
        provider = "grok"

    _active_provider[DEFAULT_SESSION_ID] = provider
    print(f"[STATE DEBUG] set_active_provider → {provider} | Inhalt: {_active_provider}")   # ← NEU

    publish(EventTypes.MODEL_CHANGED, {"provider": provider})


def get_active_provider() -> Optional[str]:
    result = _active_provider.get(DEFAULT_SESSION_ID)
    print(f"[STATE DEBUG] get_active_provider → {result} | Inhalt: {_active_provider}")     # ← NEU
    return result


def get_active_model() -> Optional[str]:
    """
    Gibt den **konkreten Modellnamen** aus den Settings zurück,
    basierend auf dem aktiven Provider.
    """
    provider = get_active_provider()
    if not provider:
        return settings.XAI_MODEL

    p = provider.lower().strip()

    if p == "ollama":
        return settings.OLLAMA_MODEL
    elif p == "grok":
        return settings.XAI_MODEL
    elif p == "openai":
        return settings.OPENAI_MODEL
    elif p == "anthropic":
        return settings.ANTHROPIC_MODEL

    return settings.XAI_MODEL


def clear_active_provider() -> None:
    """Entfernt den aktuell aktiven Provider aus dem Kontext."""
    _active_provider.pop(DEFAULT_SESSION_ID, None)
    publish(EventTypes.CONTEXT_CLEARED, {"cleared": "provider"})


# ====================== Kompatibilitäts-Alias (optional, Übergangszeit) ======================
def clear_active_model() -> None:
    """Alias für clear_active_provider (für bestehende Aufrufe)."""
    clear_active_provider()