#!/usr/bin/env python3
"""
session_manager.py - Zentrale Verwaltung von Sessions (persistent)

Verantwortlichkeiten:
- Erzeugen und Verwalten von Sessions
- Persistenz von Session-Metadaten + Context (Persona/Skill/Provider)
- Lazy Creation von Sessions
"""

import json
import datetime
from typing import Optional, Dict, Any, List
from backend.memory import get_db_connection, DEFAULT_SESSION_ID


class SessionManager:
    """Verwaltet Sessions persistent in der Datenbank."""

    def __init__(self):
        self._ensure_schema()

    def _ensure_schema(self):
        """Stellt sicher, dass die benötigten Spalten existieren."""
        conn = get_db_connection()
        cur = conn.cursor()

        # Prüfe und ergänze Spalten falls nötig (defensiv)
        cur.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in cur.fetchall()]

        if "name" not in columns:
            cur.execute("ALTER TABLE sessions ADD COLUMN name TEXT DEFAULT NULL")
        if "context" not in columns:
            cur.execute("ALTER TABLE sessions ADD COLUMN context TEXT DEFAULT NULL")

        conn.commit()
        conn.close()

    def create_session(self, name: Optional[str] = None) -> int:
        """Erzeugt eine neue Session und gibt die session_id zurück."""
        conn = get_db_connection()
        cur = conn.cursor()

        now = datetime.datetime.utcnow().isoformat() + "Z"
        display_name = name or f"Session-{now[:19]}"

        cur.execute(
            """
            INSERT INTO sessions (name, created_at, last_active, context)
            VALUES (?, ?, ?, ?)
            """,
            (display_name, now, now, None)
        )
        session_id = cur.lastrowid
        
        conn.commit()
        conn.close()
        
        SessionManager.set_current_session_id(session_id)
        return session_id

    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Gibt Metadaten + Context einer Session zurück."""
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT id, name, created_at, last_active, context FROM sessions WHERE id = ?",
            (session_id,)
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        context = json.loads(row["context"]) if row["context"] else {}

        return {
            "session_id": row["id"],
            "name": row["name"],
            "created_at": row["created_at"],
            "last_active": row["last_active"],
            "context": context
        }

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Gibt alle vorhandenen Sessions zurück."""
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT id, name, created_at, last_active FROM sessions ORDER BY last_active DESC"
        )
        rows = cur.fetchall()
        conn.close()

        return [
            {
                "session_id": row["id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "last_active": row["last_active"]
            }
            for row in rows
        ]

    def update_session_context(self, session_id: int, context: Dict[str, Any]) -> bool:
        """Speichert den transienten Context (Persona/Skill/Provider) einer Session."""
        conn = get_db_connection()
        cur = conn.cursor()

        now = datetime.datetime.utcnow().isoformat() + "Z"
        context_json = json.dumps(context, ensure_ascii=False)

        cur.execute(
            """
            UPDATE sessions 
            SET context = ?, last_active = ?
            WHERE id = ?
            """,
            (context_json, now, session_id)
        )

        success = cur.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def delete_session(self, session_id: int) -> bool:
        """Löscht eine Session (inkl. aller Messages und Memories)."""
        if session_id == DEFAULT_SESSION_ID:
            return False  # Default-Session darf nicht gelöscht werden

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        success = cur.rowcount > 0

        conn.commit()
        conn.close()
        return success

    def get_or_create_default_session(self) -> int:
        """Gibt die Default-Session zurück oder erzeugt sie bei Bedarf."""
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM sessions WHERE id = ?", (DEFAULT_SESSION_ID,))
        row = cur.fetchone()

        if row:
            conn.close()
            return DEFAULT_SESSION_ID

        # Default-Session existiert noch nicht → anlegen
        now = datetime.datetime.utcnow().isoformat() + "Z"
        cur.execute(
            """
            INSERT INTO sessions (id, name, created_at, last_active)
            VALUES (?, ?, ?, ?)
            """,
            (DEFAULT_SESSION_ID, "Default Session", now, now)
        )
        conn.commit()
        conn.close()
        return DEFAULT_SESSION_ID

    
    _current_session_id: int = DEFAULT_SESSION_ID

    @classmethod
    def get_current_session_id(cls) -> int:
        """Gibt die aktuell aktive Session zurück."""
        return cls._current_session_id


    @classmethod
    def set_current_session_id(cls, session_id: int) -> None:
        """Setzt die aktuell aktive Session."""
        cls._current_session_id = session_id


    def get_current_session(self) -> Optional[Dict[str, Any]]:
        """Gibt die aktuell aktive Session mit allen Daten zurück."""
        return self.get_session(self._current_session_id)


# Globale Instanz
session_manager = SessionManager()