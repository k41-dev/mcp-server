#!/usr/bin/env python3
"""
persona_repository.py - Single Source of Truth für Persona-Discovery und Laden
"""

from pathlib import Path
from typing import List, Dict, Optional
import re

# Wichtig: Für Struktur backend/tools/repositories/
PERSONAS_DIR = Path(__file__).resolve().parents[3] / "prompts" / "personas"


def discover_personas() -> List[Dict[str, str]]:
    """Gibt alle verfügbaren Personas mit Metadaten zurück."""
    if not PERSONAS_DIR.exists():
        print(f"[persona_repository] WARNUNG: Ordner nicht gefunden: {PERSONAS_DIR}")
        return []

    personas: List[Dict[str, str]] = []
    for file in sorted(PERSONAS_DIR.glob("*.md")):
        name = file.stem
        content = file.read_text(encoding="utf-8").strip()
        summary = _extract_summary(content)

        personas.append({
            "name": name,
            "path": str(file),
            "summary": summary,
            "content": content
        })
    return personas


def get_persona_content(persona_name: str) -> Optional[str]:
    """Lädt den vollständigen Inhalt einer Persona."""
    if not persona_name:
        return None

    persona_name = persona_name.lower().strip()
    file_path = PERSONAS_DIR / f"{persona_name}.md"

    if not file_path.exists():
        return None

    content = file_path.read_text(encoding="utf-8").strip()
    return content if content else None


def get_persona_summary(persona_name: str) -> str:
    content = get_persona_content(persona_name)
    if not content:
        return "No description available."
    return _extract_summary(content)


def _extract_summary(content: str, max_length: int = 180) -> str:
    if not content:
        return "No description available."

    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        summary = match.group(1).strip()
    else:
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        summary = lines[0] if lines else "No description."

    if len(summary) > max_length:
        summary = summary[:max_length].rsplit(" ", 1)[0] + "..."
    return summary