#!/usr/bin/env python3
"""
Migration: Fügt 'name' und 'context' Spalten zur sessions Tabelle hinzu.
"""

import sqlite3
from pathlib import Path

# Pfad zur Datenbank (angepasst an dein lokales Setup)
DB_PATH = Path(__file__).parent.parent / "data" / "chat_memory.db"

def migrate():
    if not DB_PATH.exists():
        print(f"❌ Datenbank nicht gefunden unter: {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # Aktuelle Spalten auslesen
    cur.execute("PRAGMA table_info(sessions)")
    existing_columns = [row[1] for row in cur.fetchall()]

    print(f"Aktuelle Spalten in 'sessions': {existing_columns}")

    changes_made = False

    if "name" not in existing_columns:
        print("→ Füge Spalte 'name' hinzu...")
        cur.execute("ALTER TABLE sessions ADD COLUMN name TEXT DEFAULT NULL")
        changes_made = True

    if "context" not in existing_columns:
        print("→ Füge Spalte 'context' hinzu...")
        cur.execute("ALTER TABLE sessions ADD COLUMN context TEXT DEFAULT NULL")
        changes_made = True

    if changes_made:
        conn.commit()
        print("✅ Migration erfolgreich abgeschlossen.")
    else:
        print("ℹ️  Keine Änderungen notwendig. Spalten existieren bereits.")

    conn.close()


if __name__ == "__main__":
    migrate()