#!/usr/bin/env python3
"""
state.py - Zentraler, beobachtbarer Manager für transiente Sitzungszustände
           (active persona, active skill, active provider). 
           Jetzt session-fähig vorbereitet für Multi-Agent / Multi-User.
"""

from typing import Dict, Any, Optional
from backend.memory import DEFAULT_SESSION_ID
from backend.events import publish, EventTypes
from backend.config import settings


# ====================== STATES (pro Session) ======================
_active_persona: Dict[int, Dict[str, Any]] = {}
_active_skill: Dict[int, Dict[str, Any]] = {}
_active_provider: Dict[int, str] = {}


# ====================== ACTIVE PERSONA ======================
def set_active_persona(
    persona_name: str,
    instructions: str,
    intensity: int = 7,
    session_id: int = DEFAULT_SESSION_ID
) -> None:
    """Setzt eine aktive Persona für eine bestimmte Session."""
    _active_persona[session_id] = {
        "name": persona_name.lower().strip(),
        "instructions": instructions.strip(),
        "intensity": max(1, min(10, intensity)),
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
    }
    publish(EventTypes.PERSONA_ACTIVATED, {
        "persona_name": persona_name.lower().strip(),
        "intensity": intensity,
        "session_id": session_id
    })


def get_active_persona(session_id: int = DEFAULT_SESSION_ID) -> Optional[Dict[str, Any]]:
    """Gibt die aktuell aktive Persona für die gegebene Session zurück."""
    return _active_persona.get(session_id)


def clear_active_persona(session_id: int = DEFAULT_SESSION_ID) -> None:
    """Entfernt die aktive Persona einer Session."""
    _active_persona.pop(session_id, None)
    publish(EventTypes.CONTEXT_CLEARED, {"cleared": "persona", "session_id": session_id})


# ====================== ACTIVE SKILL ======================
def set_active_skill(
    skill_name: str,
    content: str,
    session_id: int = DEFAULT_SESSION_ID
) -> None:
    """Setzt einen aktiven Skill für eine bestimmte Session."""
    _active_skill[session_id] = {
        "name": skill_name.lower().strip(),
        "content": content.strip(),
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
    }
    publish(EventTypes.SKILL_ACTIVATED, {
        "skill_name": skill_name.lower().strip(),
        "session_id": session_id
    })


def get_active_skill(session_id: int = DEFAULT_SESSION_ID) -> Optional[Dict[str, Any]]:
    """Gibt den aktuell aktiven Skill für die gegebene Session zurück."""
    return _active_skill.get(session_id)


def clear_active_skill(session_id: int = DEFAULT_SESSION_ID) -> None:
    """Entfernt den aktiven Skill einer Session."""
    _active_skill.pop(session_id, None)
    publish(EventTypes.CONTEXT_CLEARED, {"cleared": "skill", "session_id": session_id})


# ====================== ACTIVE PROVIDER ======================
def set_active_provider(
    provider: str,
    session_id: int = DEFAULT_SESSION_ID
) -> None:
    """Setzt den aktiven Provider (xai, ollama, openai, anthropic) für eine Session."""
    provider = provider.lower().strip()
    if provider not in ("xai", "ollama", "openai", "anthropic"):
        provider = "xai"

    _active_provider[session_id] = provider

    publish(EventTypes.MODEL_CHANGED, {
        "provider": provider,
        "session_id": session_id
    })


def get_active_provider(session_id: int = DEFAULT_SESSION_ID) -> Optional[str]:
    """Gibt den aktuell aktiven Provider einer Session zurück."""
    return _active_provider.get(session_id)


def get_active_model(session_id: int = DEFAULT_SESSION_ID) -> Optional[str]:
    """
    Gibt den konkreten Modellnamen zurück, basierend auf dem aktiven Provider
    der jeweiligen Session.
    """
    provider = get_active_provider(session_id)
    if not provider:
        return settings.XAI_MODEL

    p = provider.lower().strip()

    if p == "ollama":
        return settings.OLLAMA_MODEL
    elif p == "xai":
        return settings.XAI_MODEL
    elif p == "openai":
        return settings.OPENAI_MODEL
    elif p == "anthropic":
        return settings.ANTHROPIC_MODEL

    return settings.XAI_MODEL


def clear_active_provider(session_id: int = DEFAULT_SESSION_ID) -> None:
    """Entfernt den aktiven Provider einer Session."""
    _active_provider.pop(session_id, None)
    publish(EventTypes.CONTEXT_CLEARED, {"cleared": "provider", "session_id": session_id})


# ====================== Kompatibilitäts-Alias ======================
def clear_active_model(session_id: int = DEFAULT_SESSION_ID) -> None:
    """Alias für clear_active_provider (für bestehende Aufrufe)."""
    clear_active_provider(session_id)