#!/usr/bin/env python3
"""
task.py - Task / Progress Tracking Executors
"""

from typing import Dict, Any
from backend.tools.context import AgentContext
from backend.memory import store_long_term_memory


def save_phase_progress(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Speichert strukturierten Phasen-Fortschritt im Long-Term Memory.
    Wird bevorzugt für langes autonomes Arbeiten verwendet.
    """
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

    # Strukturierten Fact bauen
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
    """Gibt alle gespeicherten Phase-Progress-Einträge der aktuellen Session zurück (neueste zuerst)."""
    ctx = AgentContext.current()
    memories = recall_memories(ctx.session_id, query="PHASE PROGRESS", limit=20)
    
    if not memories:
        return {"content": [{"type": "text", "text": "No previous phase progress found."}]}
    
    # Saubere Formatierung für den Agenten
    formatted = "\n\n".join([
        f"**{m['fact'].split(chr(10))[0]}**\n{m['fact']}" 
        for m in memories
    ])
    
    return {"content": [{"type": "text", "text": formatted}]}