#!/usr/bin/env python3
"""
context.py - AgentContext: Zentrale, typsichere Abstraktionsschicht
             über dem transienten State (persona + skill + provider).

Single Source of Truth für alle Komponenten, die den aktuellen
Laufzeit-Kontext brauchen (prompt_builder, server, Tools, Logging).

Jetzt vollständig session-fähig vorbereitet für Multi-Session / Multi-Agent.
"""

import os
from typing import Optional, Dict, Any
from backend.memory import DEFAULT_SESSION_ID


class AgentContext:
    """Zentrale Laufzeit-Kontext-Klasse für den aktuellen Agenten.

    Alle Abfragen nach aktiver Persona, Skill oder Provider sollten
    **ausschließlich** über diese Klasse laufen.
    """

    def __init__(self, session_id: int = DEFAULT_SESSION_ID):
        self.session_id = session_id

    # ====================== PROPERTIES (lesen immer aus der DB) ======================
    @property
    def active_persona(self) -> Optional[Dict[str, Any]]:
        """Gibt die aktuell aktive Persona der Session zurück (direkt aus DB)."""
        try:
            from backend.tools.session_manager import session_manager
            session_data = session_manager.get_session(self.session_id)
            if session_data:
                return (session_data.get("context") or {}).get("persona")
        except Exception:
            pass
        return None

    @property
    def active_skill(self) -> Optional[Dict[str, Any]]:
        """Gibt den aktuell aktiven Skill der Session zurück (direkt aus DB)."""
        try:
            from backend.tools.session_manager import session_manager
            session_data = session_manager.get_session(self.session_id)
            if session_data:
                return (session_data.get("context") or {}).get("skill")
        except Exception:
            pass
        return None

    @property
    def has_active_skill(self) -> bool:
        return self.active_skill is not None

    @property
    def has_active_persona(self) -> bool:
        return self.active_persona is not None

    @property
    def provider(self) -> Optional[str]:
        """Gibt den aktuell aktiven Provider der Session zurück (direkt aus DB)."""
        try:
            from backend.tools.session_manager import session_manager
            session_data = session_manager.get_session(self.session_id)
            if session_data:
                return (session_data.get("context") or {}).get("provider") or "xai"
        except Exception:
            pass
        return "xai"

    @property
    def active_model(self) -> Optional[str]:
        """Gibt den konkreten Modellnamen zurück (basierend auf Provider aus DB)."""
        try:
            from backend.tools.session_manager import session_manager
            session_data = session_manager.get_session(self.session_id)
            if session_data:
                prov = (session_data.get("context") or {}).get("provider") or "xai"
                model_map = {
                    "xai": os.getenv("XAI_MODEL", "grok-4.3"),
                    "ollama": os.getenv("OLLAMA_MODEL", "llama3.1"),
                    "openai": os.getenv("OPENAI_MODEL", "gpt-4o"),
                    "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet"),
                }
                return model_map.get(prov.lower(), "grok-3")
        except Exception:
            pass
        return os.getenv("XAI_MODEL", "grok-3")

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

        if session_id == self.session_id:
            return True

        # Nur noch die Session-ID wechseln – alles andere erledigt die DB
        self.session_id = session_id
        session_manager.set_current_session_id(session_id)

        # Optional: Prompt-Cache leeren (kann man später auch weglassen)
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
        from backend.tools.session_manager import session_manager
        return cls(session_id=session_manager.get_current_session_id())


# ====================== GLOBAL DEFAULT INSTANCE ======================
default_context = AgentContext()