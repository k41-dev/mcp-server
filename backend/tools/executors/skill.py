#!/usr/bin/env python3
"""
skill.py - Skill Tools
"""

import json
from typing import Dict, Any
from backend.tools.repositories.skill_repository import discover_skills, get_skill_content
from backend.tools.state import (
    set_active_skill as _set_active_skill,
    clear_active_skill as _clear_active_skill,
)
from backend.tools.context import AgentContext


def list_skills(args: Dict[str, Any]) -> Dict[str, Any]:
    skills = discover_skills()
    if not skills:
        return {"content": [{"type": "text", "text": "No skills found in prompts/skills/"}]}

    structured = [
        {"name": s["name"], "summary": s.get("summary", "No description available.")} 
        for s in skills
    ]
    
    note = "\n\n**Hinweis:** Zur Aktivierung `execute_skill` mit Parameter `skill_name` verwenden."
    
    return {
        "content": [{
            "type": "text", 
            "text": json.dumps(structured, ensure_ascii=False, indent=2) + note
        }]
    }


def execute_skill(args: Dict[str, Any]) -> Dict[str, Any]:
    """Aktiviert einen Skill (empfohlener Weg)."""
    skill_name = args.get("skill_name", "").strip().lower()
    if not skill_name:
        return {"content": [{"type": "text", "text": "Error: skill_name is required"}], "isError": True}

    content = get_skill_content(skill_name)
    if not content:
        return {"content": [{"type": "text", "text": f"Error: Skill '{skill_name}' not found."}], "isError": True}

    _set_active_skill(skill_name, content)
    return {"content": [{"type": "text", "text": f"✅ Skill '{skill_name}' wurde aktiviert."}]}


def set_active_skill(args: Dict[str, Any]) -> Dict[str, Any]:
    """Setzt einen aktiven Skill (Legacy/Alternative zu execute_skill)."""
    skill_name = args.get("skill_name", "").strip().lower()
    content = args.get("content", "").strip()

    if not skill_name:
        return {"content": [{"type": "text", "text": "Error: skill_name is required"}], "isError": True}

    if not content:
        content = get_skill_content(skill_name)
        if not content:
            return {"content": [{"type": "text", "text": f"Error: Unknown skill '{skill_name}'."}], "isError": True}

    _set_active_skill(skill_name, content)
    return {"content": [{"type": "text", "text": f"✅ Active skill set to: {skill_name}"}]}


def get_active_skill(args: Dict[str, Any]) -> Dict[str, Any]:
    skill = AgentContext().active_skill
    if skill and isinstance(skill, dict):
        return {"content": [{"type": "text", "text": json.dumps(skill)}]}
    else:
        return {"content": [{"type": "text", "text": "No active skill"}]}


def clear_active_skill(args: Dict[str, Any]) -> Dict[str, Any]:
    _clear_active_skill()
    return {"content": [{"type": "text", "text": "✅ Active skill cleared."}]}


def get_skill(args: Dict[str, Any]) -> Dict[str, Any]:
    """Returns the full raw content of a skill (for agent inspection or advanced workflows)."""
    skill_name = args.get("skill_name", "").strip().lower()
    if not skill_name:
        return {"content": [{"type": "text", "text": "Error: skill_name is required"}], "isError": True}

    content = get_skill_content(skill_name)
    if not content:
        return {"content": [{"type": "text", "text": f"Error: Skill '{skill_name}' not found."}], "isError": True}

    return {"content": [{"type": "text", "text": content}]}