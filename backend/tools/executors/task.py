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
    """
    Gibt alle gespeicherten Phase-Progress-Einträge der aktuellen Session zurück.
    Neueste Einträge zuerst. Optimiert für LongRunningAutonomous Resume-Checks.
    """
    ctx = AgentContext.current()

    try:
        # Suche gezielt nach Phase-Progress-Einträgen
        memories = recall_memories(
            session_id=ctx.session_id,
            query="PHASE PROGRESS",
            limit=25
        )

        if not memories:
            return {
                "content": [{
                    "type": "text",
                    "text": "No phase progress records found for this session."
                }]
            }

        # Formatiere die Ergebnisse übersichtlich für den Agenten
        formatted_entries = []
        for mem in memories:
            fact = mem.get("fact", "")
            timestamp = mem.get("timestamp", "")
            formatted_entries.append(f"[{timestamp}]\n{fact}")

        result_text = "\n\n---\n\n".join(formatted_entries)

        return {
            "content": [{
                "type": "text",
                "text": f"**Phase Progress History ({len(memories)} entries):**\n\n{result_text}"
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