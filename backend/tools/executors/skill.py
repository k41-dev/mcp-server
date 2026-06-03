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
    from backend.tools.context import AgentContext

    skill_name = args.get("skill_name", "").strip().lower()
    if not skill_name:
        return {"content": [{"type": "text", "text": "Error: skill_name is required"}], "isError": True}

    content = get_skill_content(skill_name)
    if not content:
        return {"content": [{"type": "text", "text": f"Error: Skill '{skill_name}' not found."}], "isError": True}

    # Wichtig: Aktuelle Session verwenden
    ctx = AgentContext.current()
    _set_active_skill(skill_name, content, session_id=ctx.session_id)

    # === Leichtes Debug ===
    print(f"[SKILL DEBUG] execute_skill erfolgreich: '{skill_name}' → Session {ctx.session_id}")
    # === Ende Debug ===

    return {
        "content": [{
            "type": "text",
            "text": f"✅ Skill '{skill_name}' wurde in Session {ctx.session_id} aktiviert."
        }]
    }


def set_active_skill(args: Dict[str, Any]) -> Dict[str, Any]:
    """Setzt einen aktiven Skill (Legacy/Alternative zu execute_skill)."""
    from backend.tools.context import AgentContext

    skill_name = args.get("skill_name", "").strip().lower()
    content = args.get("content", "").strip()

    if not skill_name:
        return {"content": [{"type": "text", "text": "Error: skill_name is required"}], "isError": True}

    if not content:
        content = get_skill_content(skill_name)
        if not content:
            return {"content": [{"type": "text", "text": f"Error: Unknown skill '{skill_name}'."}], "isError": True}

    # Wichtig: Aktuelle Session verwenden
    ctx = AgentContext.current()
    _set_active_skill(skill_name, content, session_id=ctx.session_id)

    return {
        "content": [{
            "type": "text",
            "text": f"✅ Active skill set to: {skill_name} in Session {ctx.session_id}"
        }]
    }


def get_active_skill(args: Dict[str, Any]) -> Dict[str, Any]:
    from backend.tools.context import AgentContext
    from backend.tools.session_manager import session_manager

    ctx = AgentContext.current()
    skill = ctx.active_skill

    if (not skill or 
        not isinstance(skill, dict) or 
        not skill.get("name") or 
        str(skill.get("name")).lower().strip() in ("", "none")):
        
        try:
            session_data = session_manager.get_session(ctx.session_id)
            if session_data and session_data.get("context", {}).get("skill"):
                skill = session_data["context"]["skill"]
        except Exception:
            pass

    if skill and isinstance(skill, dict):
        return {"content": [{"type": "text", "text": json.dumps(skill)}]}
    else:
        return {"content": [{"type": "text", "text": "No active skill"}]}


def clear_active_skill(args: Dict[str, Any]) -> Dict[str, Any]:
    from backend.tools.context import AgentContext

    ctx = AgentContext.current()
    _clear_active_skill(session_id=ctx.session_id)

    return {
        "content": [{
            "type": "text",
            "text": f"✅ Active skill cleared in Session {ctx.session_id}."
        }]
    }


def get_skill(args: Dict[str, Any]) -> Dict[str, Any]:
    """Returns the full raw content of a skill (for agent inspection or advanced workflows)."""
    skill_name = args.get("skill_name", "").strip().lower()
    if not skill_name:
        return {"content": [{"type": "text", "text": "Error: skill_name is required"}], "isError": True}

    content = get_skill_content(skill_name)
    if not content:
        return {"content": [{"type": "text", "text": f"Error: Skill '{skill_name}' not found."}], "isError": True}

    return {"content": [{"type": "text", "text": content}]}