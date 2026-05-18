#!/usr/bin/env python3
"""
context.py - AgentContext: Zentrale, typsichere Abstraktionsschicht
             über dem transienten State (persona + skill).

Single Source of Truth für alle Komponenten, die den aktuellen
Laufzeit-Kontext brauchen (prompt_builder, server, Tools, Logging).

Design-Prinzipien:
- Minimal-invasiv
- Leicht testbar (einfach zu mocken)
- Vorbereitet auf Multi-Session (session_id als Parameter)
- Keine Business-Logik — nur Query-Interface + Convenience-Methoden
"""

from typing import Optional, Dict, Any
from backend.tools.state import (
    get_active_persona as _get_active_persona,
    get_active_skill as _get_active_skill,
)
from backend.memory import DEFAULT_SESSION_ID


class AgentContext:
    """Zentrale Laufzeit-Kontext-Klasse für den aktuellen Agenten.

    Alle Abfragen nach aktiver Persona oder Skill sollten **ausschließlich**
    über diese Klasse laufen (nicht direkt auf state.py).
    """

    def __init__(self, session_id: int = DEFAULT_SESSION_ID):
        self.session_id = session_id

    # ====================== PROPERTIES ======================

    @property
    def active_persona(self) -> Optional[Dict[str, Any]]:
        """Gibt die aktuell aktive Persona zurück oder None."""
        return _get_active_persona()

    @property
    def active_skill(self) -> Optional[Dict[str, Any]]:
        """Gibt den aktuell aktiven Skill zurück oder None."""
        return _get_active_skill()

    @property
    def has_active_skill(self) -> bool:
        return self.active_skill is not None

    @property
    def has_active_persona(self) -> bool:
        return self.active_persona is not None

    # ====================== CONVENIENCE ======================

    def get_prompt_injection(self) -> str:
        """Liefert den fertigen Prompt-Injection-String für Persona + Skill.

        Skill hat Vorrang und wird zuerst angehängt.
        """
        parts: list[str] = []

        if self.active_skill:
            skill = self.active_skill
            parts.append(
                f"**AKTIVER SKILL: {skill.get('name', 'unknown').upper()}**\n{skill.get('content', '')}"
            )
            parts.append(
                "\n**Hinweis:** Die Anweisungen des aktiven Skills haben Vorrang "
                "vor dem Persona-Stil, falls es zu Konflikten kommt."
            )

        if self.active_persona:
            persona = self.active_persona
            parts.append(
                f"**AKTIVE PERSONA: {persona.get('name', 'unknown').upper()}**\n{persona.get('instructions', '')}"
            )

        return "\n\n".join(parts) if parts else ""

    def get_active_names(self) -> Dict[str, Optional[str]]:
        """Gibt nur die Namen zurück (für Logging / Status)."""
        return {
            "persona": self.active_persona.get("name") if self.active_persona else None,
            "skill": self.active_skill.get("name") if self.active_skill else None,
        }

    def get_context_summary(self) -> str:
        """Kurze, menschenlesbare Zusammenfassung des aktuellen Kontexts."""
        names = self.get_active_names()
        if names["skill"] and names["persona"]:
            return f"{names['skill']} + {names['persona']}"
        elif names["skill"]:
            return names["skill"]
        elif names["persona"]:
            return names["persona"]
        else:
            return "Default (keine Persona/Skill aktiv)"

    def to_dict(self) -> Dict[str, Any]:
        """Gibt den kompletten aktuellen Kontext als Dictionary zurück.

        Sehr nützlich für get_prompt_status, Logging und Debugging.
        """
        return {
            "session_id": self.session_id,
            "active_persona": self.active_persona,
            "active_skill": self.active_skill,
            "has_active_persona": self.has_active_persona,
            "has_active_skill": self.has_active_skill,
            "summary": self.get_context_summary(),
        }

    def __repr__(self) -> str:
        names = self.get_active_names()
        return f"AgentContext(persona={names['persona']}, skill={names['skill']})"

    # ====================== CLASSMETHODS ======================

    @classmethod
    def current(cls) -> "AgentContext":
        """Gibt die Default-Instanz zurück (bequem für schnelle Zugriffe)."""
        return default_context


# ====================== GLOBAL DEFAULT INSTANCE ======================
default_context = AgentContext()