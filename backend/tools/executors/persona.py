#!/usr/bin/env python3
"""
persona.py - Persona Tools
"""

import json
from typing import Dict, Any
from backend.tools.repositories.persona_repository import discover_personas, get_persona_content
from backend.tools.state import (
    set_active_persona as _set_active_persona,
    clear_active_persona as _clear_active_persona,
)
from backend.tools.context import AgentContext


def set_active_persona(args: Dict[str, Any]) -> Dict[str, Any]:
    """Setzt eine Persona (lädt bei Bedarf automatisch aus dem Repository)."""
    from backend.tools.context import AgentContext

    persona_name = args.get("persona_name", "").strip().lower()
    instructions = args.get("instructions", "").strip()
    intensity = min(max(int(args.get("intensity", 7)), 1), 10)

    if not persona_name:
        return {"content": [{"type": "text", "text": "Error: persona_name is required"}], "isError": True}

    # Wenn keine Instructions übergeben wurden → aus Repository laden
    if not instructions:
        instructions = get_persona_content(persona_name)
        if not instructions:
            return {"content": [{"type": "text", "text": f"Error: Unknown persona '{persona_name}'."}], "isError": True}

    # Wichtig: Aktuelle Session verwenden
    ctx = AgentContext.current()
    _set_active_persona(persona_name, instructions, intensity, session_id=ctx.session_id)

    return {
        "content": [{
            "type": "text",
            "text": f"✅ Active persona set to: {persona_name} (intensity={intensity}) in Session {ctx.session_id}"
        }]
    }


def get_active_persona(args: Dict[str, Any]) -> Dict[str, Any]:
    persona = AgentContext.current().active_persona
    if persona and isinstance(persona, dict):
        return {"content": [{"type": "text", "text": json.dumps(persona)}]}
    else:
        return {"content": [{"type": "text", "text": "No active persona"}]}


def clear_active_persona(args: Dict[str, Any]) -> Dict[str, Any]:
    from backend.tools.context import AgentContext

    ctx = AgentContext.current()
    _clear_active_persona(session_id=ctx.session_id)

    return {
        "content": [{
            "type": "text",
            "text": f"✅ Active persona cleared in Session {ctx.session_id}."
        }]
    }


def list_personas(args: Dict[str, Any]) -> Dict[str, Any]:
    personas = discover_personas()
    if not personas:
        return {"content": [{"type": "text", "text": "No personas found in prompts/personas/"}]}

    structured = [
        {"name": p["name"], "summary": p["summary"]} 
        for p in personas
    ]
    
    return {
        "content": [{
            "type": "text", 
            "text": json.dumps(structured, ensure_ascii=False, indent=2)
        }]
    }


def get_persona(args: Dict[str, Any]) -> Dict[str, Any]:
    """Returns the full raw content of a persona (for agent inspection or advanced workflows)."""
    persona_name = args.get("persona_name", "").strip().lower()
    if not persona_name:
        return {"content": [{"type": "text", "text": "Error: persona_name is required"}], "isError": True}

    content = get_persona_content(persona_name)
    if not content:
        return {"content": [{"type": "text", "text": f"Error: Persona '{persona_name}' not found."}], "isError": True}

    return {"content": [{"type": "text", "text": content}]}