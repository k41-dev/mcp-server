#!/usr/bin/env python3
"""
context.py - AgentContext: Zentrale, typsichere Abstraktionsschicht
             über dem transienten State (persona + skill + provider).

Single Source of Truth für alle Komponenten, die den aktuellen
Laufzeit-Kontext brauchen (prompt_builder, server, Tools, Logging).

Jetzt vollständig session-fähig vorbereitet für Multi-Session / Multi-Agent.
"""

from typing import Optional, Dict, Any
from backend.tools.state import (
    get_active_persona as _get_active_persona,
    get_active_skill as _get_active_skill,
    get_active_provider as _get_active_provider,
    get_active_model as _get_active_model,
)
from backend.memory import DEFAULT_SESSION_ID


class AgentContext:
    """Zentrale Laufzeit-Kontext-Klasse für den aktuellen Agenten.

    Alle Abfragen nach aktiver Persona, Skill oder Provider sollten
    **ausschließlich** über diese Klasse laufen.
    """

    def __init__(self, session_id: int = DEFAULT_SESSION_ID):
        self.session_id = session_id

    # ====================== PROPERTIES ======================
    @property
    def active_persona(self) -> Optional[Dict[str, Any]]:
        """Gibt die aktuell aktive Persona der Session zurück oder None."""
        return _get_active_persona(session_id=self.session_id)

    @property
    def active_skill(self) -> Optional[Dict[str, Any]]:
        """Gibt den aktuell aktiven Skill der Session zurück oder None."""
        return _get_active_skill(session_id=self.session_id)

    @property
    def has_active_skill(self) -> bool:
        return self.active_skill is not None

    @property
    def has_active_persona(self) -> bool:
        return self.active_persona is not None

    @property
    def provider(self) -> Optional[str]:
        """Gibt den aktuell aktiven Provider der Session zurück."""
        return _get_active_provider(session_id=self.session_id)

    @property
    def active_model(self) -> Optional[str]:
        """
        Gibt den **konkreten Modellnamen** der Session zurück,
        basierend auf dem aktiven Provider.
        """
        return _get_active_model(session_id=self.session_id)

    # ====================== CONVENIENCE ======================
    def get_prompt_injection(self) -> str:
        """Liefert den fertigen Prompt-Injection-String für Persona + Skill.

        Garantiert, dass beide (falls aktiv) immer enthalten sind.
        Skill hat Vorrang vor Persona.
        """
        parts: list[str] = []

        if self.active_skill:
            skill = self.active_skill
            parts.append(
                f"**AKTIVER SKILL: {skill['name'].upper()}**\n{skill['content']}"
            )

        if self.active_persona:
            persona = self.active_persona
            parts.append(
                f"**AKTIVE PERSONA: {persona['name'].upper()}**\n{persona['instructions']}"
            )

        if self.active_skill and self.active_persona:
            parts.append(
                "**Hinweis:** Der aktive Skill hat Vorrang vor der Persona, "
                "falls es zu Konflikten kommt."
            )

        return "\n\n".join(parts) if parts else ""

    def get_active_names(self) -> Dict[str, Optional[str]]:
        """Gibt die Namen der aktiven Komponenten der aktuellen Session zurück."""
        return {
            "provider": self.provider,
            "model": self.active_model,
            "persona": self.active_persona.get("name") if self.active_persona else None,
            "skill": self.active_skill.get("name") if self.active_skill else None,
        }

    def get_context_summary(self) -> str:
        """Kurze, menschenlesbare Zusammenfassung des aktuellen Kontexts der Session."""
        names = self.get_active_names()
        parts = []
        if names["model"]:
            parts.append(names["model"])
        if names["provider"]:
            parts.append(f"({names['provider']})")
        if names["skill"]:
            parts.append(names["skill"])
        if names["persona"]:
            parts.append(names["persona"])

        return " + ".join(parts) if parts else "Default (no model/persona/skill active)"

    def to_dict(self) -> Dict[str, Any]:
        """Gibt den kompletten aktuellen Kontext der Session als Dictionary zurück."""
        return {
            "session_id": self.session_id,
            "provider": self.provider,
            "active_model": self.active_model,
            "active_persona": self.active_persona,
            "active_skill": self.active_skill,
            "has_active_persona": self.has_active_persona,
            "has_active_skill": self.has_active_skill,
            "summary": self.get_context_summary(),
        }

    def __repr__(self) -> str:
        names = self.get_active_names()
        return (
            f"AgentContext(session_id={self.session_id}, "
            f"persona={names['persona']}, skill={names['skill']}, "
            f"provider={names['provider']})"
        )

    # ====================== CLASSMETHODS ======================
    @classmethod
    def current(cls) -> "AgentContext":
        """Gibt die Default-Instanz zurück (bequem für schnelle Zugriffe)."""
        return default_context


# ====================== GLOBAL DEFAULT INSTANCE ======================
default_context = AgentContext()