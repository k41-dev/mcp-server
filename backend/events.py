#!/usr/bin/env python3
"""
events.py - Leichter, zentraler Event Bus für State Changes

Ermöglicht Entkopplung zwischen State-Änderungen (Persona/Skill)
und anderen Komponenten (z. B. Prompt-Cache, Logging, Audit).

Design: Minimal, erweiterbar, thread-sicher genug für unseren Use-Case.
"""

import logging
from typing import Callable, Dict, List, Any
from threading import Lock

logger = logging.getLogger("mcp.events")

# Globale Event-Registry
_subscribers: Dict[str, List[Callable]] = {}
_lock = Lock()


def subscribe(event_type: str, callback: Callable[[dict], None]) -> None:
    """
    Registriert eine Callback-Funktion für einen bestimmten Event-Typ.
    """
    with _lock:
        if event_type not in _subscribers:
            _subscribers[event_type] = []
        _subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to '{event_type}' → {callback.__name__}")


def publish(event_type: str, data: dict = None) -> None:
    """
    Feuert ein Event und ruft alle registrierten Callbacks auf.
    """
    data = data or {}
    data["event_type"] = event_type
    data["timestamp"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"

    with _lock:
        callbacks = _subscribers.get(event_type, []).copy()

    if not callbacks:
        return

    for callback in callbacks:
        try:
            callback(data)
        except Exception as e:
            logger.error(f"Error in event callback for '{event_type}': {e}")


# Vordefinierte Event-Typen (für Konsistenz)
class EventTypes:
    PERSONA_ACTIVATED = "persona_activated"
    SKILL_ACTIVATED = "skill_activated"
    CONTEXT_CLEARED = "context_cleared"
    MEMORY_CLEARED = "memory_cleared"
    MODEL_CHANGED = "model_changed"


# ====================== DEFAULT LOGGING SUBSCRIBER ======================
def _log_state_change(data: dict) -> None:
    """Standard-Subscriber: Protokolliert alle Persona/Skill State-Changes."""
    event = data.get("event_type", "unknown")
    timestamp = data.get("timestamp", "")

    if event == EventTypes.PERSONA_ACTIVATED:
        logger.info(f"🎭 Persona aktiviert: {data.get('persona_name')} (Intensität: {data.get('intensity')})")
    elif event == EventTypes.SKILL_ACTIVATED:
        logger.info(f"🛠️ Skill aktiviert: {data.get('skill_name')}")
    elif event == EventTypes.CONTEXT_CLEARED:
        logger.info(f"🧹 Context zurückgesetzt: {data.get('cleared', 'unknown')}")
    else:
        logger.debug(f"Event empfangen: {event} → {data}")


# Automatisch beim Import abonnieren
subscribe(EventTypes.PERSONA_ACTIVATED, _log_state_change)
subscribe(EventTypes.SKILL_ACTIVATED, _log_state_change)
subscribe(EventTypes.CONTEXT_CLEARED, _log_state_change)

logger.info("✅ Event Bus mit Logging-Subscriber initialisiert")