#!/usr/bin/env python3
"""
state.py - Zentraler, beobachtbarer Manager für transiente Sitzungszustände
           (active persona, active skill). Single Source of Truth.
"""

from typing import Dict, Any, Optional
from backend.memory import DEFAULT_SESSION_ID
from backend.events import publish, EventTypes

# Nur hier darf der State leben
_active_persona: Dict[int, Dict[str, Any]] = {}
_active_skill: Dict[int, Dict[str, Any]] = {}
_active_model: Dict[int, str] = {}


def set_active_persona(persona_name: str, instructions: str, intensity: int = 7) -> None:
    _active_persona[DEFAULT_SESSION_ID] = {
        "name": persona_name.lower().strip(),
        "instructions": instructions.strip(),
        "intensity": max(1, min(10, intensity)),
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
    }

    # === Event feuern ===
    publish(EventTypes.PERSONA_ACTIVATED, {
        "persona_name": persona_name.lower().strip(),
        "intensity": intensity
    })


def get_active_persona() -> Optional[Dict[str, Any]]:
    return _active_persona.get(DEFAULT_SESSION_ID)


def clear_active_persona() -> None:
    _active_persona.pop(DEFAULT_SESSION_ID, None)

    # === Event feuern ===
    publish(EventTypes.CONTEXT_CLEARED, {"cleared": "persona"})


def set_active_skill(skill_name: str, content: str) -> None:
    _active_skill[DEFAULT_SESSION_ID] = {
        "name": skill_name.lower().strip(),
        "content": content.strip(),
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
    }

    # === Event feuern ===
    publish(EventTypes.SKILL_ACTIVATED, {
        "skill_name": skill_name.lower().strip()
    })


def get_active_skill() -> Optional[Dict[str, Any]]:
    return _active_skill.get(DEFAULT_SESSION_ID)


def clear_active_skill() -> None:
    _active_skill.pop(DEFAULT_SESSION_ID, None)

    # === Event feuern ===
    publish(EventTypes.CONTEXT_CLEARED, {"cleared": "skill"})


# ====================== ACTIVE MODEL ======================
def set_active_model(model_name: str) -> None:
    """Setzt das aktuell aktive Modell (z. B. 'grok', 'ollama', 'openai', 'anthropic')."""
    model_name = model_name.lower().strip()
    if model_name not in ("grok", "ollama", "openai", "anthropic"):
        model_name = "grok"  # sicherer Default

    _active_model[DEFAULT_SESSION_ID] = model_name

    publish(EventTypes.MODEL_CHANGED, {
        "model": model_name
    })


def get_active_model() -> Optional[str]:
    return _active_model.get(DEFAULT_SESSION_ID)


def clear_active_model() -> None:
    _active_model.pop(DEFAULT_SESSION_ID, None)
    publish(EventTypes.CONTEXT_CLEARED, {"cleared": "model"})