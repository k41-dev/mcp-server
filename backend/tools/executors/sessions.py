#!/usr/bin/env python3
"""
sessions.py - Session Management Executors
"""

from typing import Dict, Any
from backend.tools.session_manager import session_manager


def create_session(args: Dict[str, Any]) -> Dict[str, Any]:
    """Erzeugt eine neue Session."""
    name = args.get("name", "").strip() or None

    try:
        session_id = session_manager.create_session(name=name)
        return {
            "content": [{
                "type": "text",
                "text": f"✅ Session erstellt (ID: {session_id})"
            }]
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error creating session: {str(e)}"}],
            "isError": True
        }


def list_sessions(args: Dict[str, Any]) -> Dict[str, Any]:
    """Listet alle vorhandenen Sessions auf."""
    try:
        sessions = session_manager.list_sessions()

        if not sessions:
            return {
                "content": [{"type": "text", "text": "Keine Sessions vorhanden."}]
            }

        lines = []
        for s in sessions:
            lines.append(f"• ID: {s['session_id']} | Name: {s['name']} | Last active: {s['last_active']}")

        text = "**Vorhandene Sessions:**\n" + "\n".join(lines)

        return {
            "content": [{"type": "text", "text": text}]
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error listing sessions: {str(e)}"}],
            "isError": True
        }


def get_session(args: Dict[str, Any]) -> Dict[str, Any]:
    """Gibt Details zu einer bestimmten Session zurück."""
    session_id = args.get("session_id")

    if not session_id:
        return {
            "content": [{"type": "text", "text": "Error: session_id ist erforderlich"}],
            "isError": True
        }

    try:
        session = session_manager.get_session(int(session_id))

        if not session:
            return {
                "content": [{"type": "text", "text": f"Session mit ID {session_id} nicht gefunden."}],
                "isError": True
            }

        import json
        text = json.dumps(session, indent=2, ensure_ascii=False)

        return {
            "content": [{"type": "text", "text": text}]
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error getting session: {str(e)}"}],
            "isError": True
        }


def switch_session(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wechselt in eine andere Session und lädt deren gespeicherten Context.
    Nutzt die saubere Session-Verwaltung über SessionManager.
    """
    from backend.tools.context import AgentContext

    session_id = args.get("session_id")

    if not session_id:
        return {
            "content": [{"type": "text", "text": "Error: session_id ist erforderlich"}],
            "isError": True
        }

    try:
        session_id = int(session_id)
        ctx = AgentContext.current()                    # ← sauber über current()

        success = ctx.switch_to_session(session_id)

        if success:
            return {
                "content": [{
                    "type": "text",
                    "text": f"✅ Erfolgreich zu Session {session_id} gewechselt."
                }]
            }
        else:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Session {session_id} nicht gefunden."
                }],
                "isError": True
            }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error beim Session-Wechsel: {str(e)}"}],
            "isError": True
        }


def save_current_context(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Speichert den aktuellen Context in die aktuelle Session.
    Nutzt AgentContext.current() für korrekte Session-Zuordnung.
    """
    from backend.tools.context import AgentContext

    try:
        ctx = AgentContext.current()                    # ← wichtig!

        # Optional: session_id aus Argumenten erlauben (für Flexibilität)
        session_id = args.get("session_id")
        target_session = int(session_id) if session_id else None

        success = ctx.save_context_to_session(session_id=target_session)

        if success:
            active_session = target_session or ctx.session_id
            return {
                "content": [{
                    "type": "text",
                    "text": f"✅ Context in Session {active_session} gespeichert."
                }]
            }
        else:
            return {
                "content": [{
                    "type": "text",
                    "text": "Context konnte nicht gespeichert werden."
                }],
                "isError": True
            }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error beim Speichern: {str(e)}"}],
            "isError": True
        }