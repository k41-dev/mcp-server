#!/usr/bin/env python3
"""
Migration: Fügt 'name' und 'context' Spalten zur sessions Tabelle hinzu.
Funktioniert sowohl lokal als auch im Docker-Container.
"""

import sqlite3
from pathlib import Path

def find_database_path() -> Path:
    """
    Versucht, die Datenbank automatisch zu finden.
    Funktioniert sowohl lokal als auch im Container.
    """
    # Mögliche Pfade (in Reihenfolge der Wahrscheinlichkeit)
    possible_paths = [
        # Docker Container
        Path("/app/data/chat_memory.db"),
        # Lokal, wenn Script neben backend/ liegt
        Path(__file__).parent / "data" / "chat_memory.db",
        # Lokal, wenn Script im Root liegt
        Path.cwd() / "data" / "chat_memory.db",
        # Fallback: eine Ebene höher
        Path(__file__).parent.parent / "data" / "chat_memory.db",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    # Wenn nichts gefunden wurde, gib den wahrscheinlichsten Pfad zurück
    return Path("/app/data/chat_memory.db")


def migrate():
    db_path = find_database_path()

    if not db_path.exists():
        print(f"❌ Datenbank nicht gefunden unter: {db_path}")
        print("   Bitte stelle sicher, dass der Container läuft oder der Pfad korrekt ist.")
        return

    print(f"📁 Verwende Datenbank: {db_path}")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Aktuelle Spalten auslesen
    cur.execute("PRAGMA table_info(sessions)")
    existing_columns = [row[1] for row in cur.fetchall()]

    print(f"Aktuelle Spalten: {existing_columns}")

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
        print("ℹ️  Keine Änderungen notwendig. Alle Spalten existieren bereits.")

    conn.close()


if __name__ == "__main__":
    migrate()