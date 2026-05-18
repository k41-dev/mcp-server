#!/usr/bin/env python3
"""
skill_repository.py - Single Source of Truth für Skill-Discovery und Laden
"""

from pathlib import Path
from typing import List, Dict, Optional
import re

# Wichtig: Angepasst für neue Struktur backend/tools/repositories/
SKILLS_DIR = Path(__file__).resolve().parents[3] / "prompts" / "skills"


def discover_skills() -> List[Dict[str, str]]:
    """Gibt alle verfügbaren Skills mit Metadaten zurück."""
    if not SKILLS_DIR.exists():
        return []

    skills: List[Dict[str, str]] = []
    for file in sorted(SKILLS_DIR.glob("*.md")):
        name = file.stem
        content = file.read_text(encoding="utf-8").strip()
        summary = _extract_summary(content)

        skills.append({
            "name": name,
            "path": str(file),
            "summary": summary,
            "content": content
        })
    return skills


def get_skill_content(skill_name: str) -> Optional[str]:
    """Lädt den vollständigen Inhalt eines Skills."""
    if not skill_name:
        return None

    skill_name = skill_name.lower().strip()
    file_path = SKILLS_DIR / f"{skill_name}.md"

    if not file_path.exists():
        return None

    content = file_path.read_text(encoding="utf-8").strip()
    return content if content else None


def get_skill_summary(skill_name: str) -> str:
    """Gibt nur die kurze Zusammenfassung eines Skills zurück."""
    content = get_skill_content(skill_name)
    if not content:
        return "No description available."
    return _extract_summary(content)


def _extract_summary(content: str, max_length: int = 180) -> str:
    """Extrahiert eine kurze Beschreibung aus dem Skill-Inhalt."""
    if not content:
        return "No description available."

    # Versuche zuerst, die erste Überschrift zu finden
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        summary = match.group(1).strip()
    else:
        # Fallback: erste nicht-leere Zeile
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        summary = lines[0] if lines else "No description."

    if len(summary) > max_length:
        summary = summary[:max_length].rsplit(" ", 1)[0] + "..."
    return summary