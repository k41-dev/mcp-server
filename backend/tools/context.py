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


    # ====================== Session ======================
    def switch_to_session(self, session_id: int) -> bool:
        from backend.tools.session_manager import session_manager
        from backend.tools.state import (
            set_active_persona, set_active_skill, set_active_provider,
            clear_active_persona, clear_active_skill, clear_active_provider,
            get_active_provider as _get_active_provider,
        )

        self.save_context_to_session()

        session_data = session_manager.get_session(session_id)
        if not session_data:
            return False

        context = session_data.get("context", {}) or {}

        clear_active_persona(session_id=self.session_id)
        clear_active_skill(session_id=self.session_id)
        clear_active_provider(session_id=self.session_id)

        # === Provider ===
        saved_provider = context.get("provider") if isinstance(context, dict) else None

        if saved_provider:
            # Es gibt einen gespeicherten Provider → diesen wiederherstellen
            set_active_provider(saved_provider, session_id=session_id)
        else:
            # Kein Provider in dieser Session gespeichert → sauber auf Default
            set_active_provider("xai", session_id=session_id)

        # Persona & Skill wie bisher
        if context.get("persona"):
            p = context["persona"]
            set_active_persona(
                p.get("name", ""), 
                p.get("instructions", ""), 
                p.get("intensity", 7), 
                session_id=session_id
            )

        if context.get("skill"):
            s = context["skill"]
            set_active_skill(
                s.get("name", ""), 
                s.get("content", ""), 
                session_id=session_id
            )

        self.session_id = session_id
        session_manager.set_current_session_id(session_id)

        try:
            from backend.prompt_cache import clear_cache
            clear_cache()
        except Exception:
            pass
            
        return True


    def save_context_to_session(self, session_id: Optional[int] = None) -> bool:
        """
        Speichert den aktuellen transienten Context (Persona, Skill, Provider)
        in die angegebene Session (oder in die aktuelle Session).
        """
        from backend.tools.session_manager import session_manager

        target_session = session_id or self.session_id

        context_data = {
            "persona": self.active_persona,
            "skill": self.active_skill,
            "provider": self.provider,
        }

        return session_manager.update_session_context(target_session, context_data)

    # ====================== CLASSMETHODS ======================
    @classmethod
    def current(cls) -> "AgentContext":
        """Gibt eine AgentContext-Instanz für die aktuell aktive Session zurück."""
        from backend.tools.session_manager import session_manager
        return cls(session_id=session_manager.get_current_session_id())


# ====================== GLOBAL DEFAULT INSTANCE ======================
default_context = AgentContext()