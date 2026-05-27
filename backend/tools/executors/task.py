#!/usr/bin/env python3
"""
task.py - Task / Progress Tracking Executors
"""

from typing import Dict, Any
from backend.tools.context import AgentContext


def save_phase_progress(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Speichert strukturierten Phasen-Fortschritt im Long-Term Memory.
    """
    from backend.memory import store_long_term_memory

    ctx = AgentContext.current()

    phase_name = args.get("phase_name", "").strip()
    status = args.get("status", "").strip()
    summary = args.get("summary", "").strip()
    next_step = args.get("next_step", "").strip()
    notes = args.get("notes", "").strip()

    if not phase_name or not status or not summary:
        return {
            "content": [{
                "type": "text",
                "text": "Error: phase_name, status and summary are required"
            }],
            "isError": True
        }

    fact_parts = [
        f"[PHASE PROGRESS] {phase_name}",
        f"Status: {status}",
        f"Summary: {summary}"
    ]
    if next_step:
        fact_parts.append(f"Next step: {next_step}")
    if notes:
        fact_parts.append(f"Notes: {notes}")

    fact = "\n".join(fact_parts)

    mem_id = store_long_term_memory(
        session_id=ctx.session_id,
        fact=fact,
        source="phase_progress"
    )

    return {
        "content": [{
            "type": "text",
            "text": f"✅ Phase progress saved (id={mem_id}) | Phase: {phase_name} | Status: {status}"
        }]
    }


def get_phase_progress(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gibt gespeicherte Phase-Progress-Einträge zurück.
    Optional kann mit 'project' nach einem bestimmten Projekt gefiltert werden.
    """
    from backend.memory import recall_memories

    ctx = AgentContext.current()
    project_filter = args.get("project", "").strip().lower()

    try:
        memories = recall_memories(
            session_id=ctx.session_id,
            query="PHASE PROGRESS",
            limit=30
        )

        if not memories:
            return {
                "content": [{
                    "type": "text",
                    "text": "No phase progress records found for this session."
                }]
            }

        # Optional filtern nach Projekt
        if project_filter:
            memories = [
                m for m in memories 
                if project_filter in m.get("fact", "").lower()
            ]

        if not memories:
            return {
                "content": [{
                    "type": "text",
                    "text": f"No phase progress records found for project '{project_filter}'."
                }]
            }

        # Strukturierte Ausgabe
        formatted = []
        for mem in memories:
            fact = mem.get("fact", "")
            timestamp = mem.get("timestamp", "")
            formatted.append({
                "timestamp": timestamp,
                "content": fact
            })

        import json
        result = json.dumps(formatted, ensure_ascii=False, indent=2)

        return {
            "content": [{
                "type": "text",
                "text": f"**Phase Progress Records ({len(formatted)} found):**\n\n{result}"
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error retrieving phase progress: {str(e)}"
            }],
            "isError": True
        }