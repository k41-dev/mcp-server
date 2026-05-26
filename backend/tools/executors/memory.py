#!/usr/bin/env python3
"""
memory.py - Memory Tools
"""

from typing import Dict, Any
from backend.tools.context import AgentContext
from backend.memory import (
    store_long_term_memory,
    recall_memories,
    list_all_memories,
    clear_long_term_memory,
    get_recent_messages,
    add_message,
    full_reset as _full_reset,
)
# Alias für clear_chat_history, da der Name im Executor gleich ist
from backend.memory import clear_chat_history as _clear_chat_history_core


def store_memory(args: Dict[str, Any]) -> Dict[str, Any]:
    """Speichert einen Fakt im Long-Term Memory der aktuellen Session."""
    ctx = AgentContext.current()
    fact = args.get("fact", "").strip()
    if not fact:
        return {"content": [{"type": "text", "text": "Error: fact is required"}], "isError": True}

    source = args.get("source", "agent")
    mem_id = store_long_term_memory(ctx.session_id, fact, source)

    return {"content": [{"type": "text", "text": f"✅ Memory stored (id={mem_id})"}]}


def recall_memory(args: Dict[str, Any]) -> Dict[str, Any]:
    """Ruft relevante Long-Term Memories der aktuellen Session ab."""
    ctx = AgentContext.current()
    query = args.get("query", "")
    limit = args.get("limit", 8)

    memories = recall_memories(ctx.session_id, query, limit)
    if not memories:
        return {"content": [{"type": "text", "text": "No relevant memories found."}]}

    text = "\n".join([f"• {m['fact']}" for m in memories])
    return {"content": [{"type": "text", "text": text}]}


def list_memories(args: Dict[str, Any]) -> Dict[str, Any]:
    """Listet alle Long-Term Memories der aktuellen Session auf."""
    ctx = AgentContext.current()
    memories = list_all_memories(ctx.session_id)
    if not memories:
        return {"content": [{"type": "text", "text": "No memories stored yet."}]}

    text = "\n".join([f"• {m['fact']}" for m in memories])
    return {"content": [{"type": "text", "text": text}]}


def clear_memory(args: Dict[str, Any]) -> Dict[str, Any]:
    """Löscht das Long-Term Memory der aktuellen Session (nicht global)."""
    ctx = AgentContext.current()
    clear_long_term_memory(session_id=ctx.session_id)

    return {
        "content": [{
            "type": "text",
            "text": f"🗑️ Long-term memory cleared (Session {ctx.session_id})."
        }]
    }


def clear_chat_history(args: Dict[str, Any]) -> Dict[str, Any]:
    """Löscht die Chat-History der aktuellen Session (nicht global)."""
    ctx = AgentContext.current()
    _clear_chat_history_core(session_id=ctx.session_id)

    return {
        "content": [{
            "type": "text",
            "text": f"🗑️ Chat history cleared (Session {ctx.session_id})."
        }]
    }


def list_chat_history(args: Dict[str, Any]) -> Dict[str, Any]:
    """Listet die Chat-History der aktuellen Session auf."""
    ctx = AgentContext.current()
    limit = args.get("limit", 20)
    messages = get_recent_messages(ctx.session_id, limit)

    if not messages:
        return {"content": [{"type": "text", "text": "No chat history."}]}

    text = "\n".join([f"{m['role']}: {m['content'][:120]}" for m in messages])
    return {"content": [{"type": "text", "text": text}]}


def full_reset(args: Dict[str, Any]) -> Dict[str, Any]:
    """Nuclear wipe – löscht die gesamte Datenbank (alle Sessions)."""
    _full_reset()
    return {"content": [{"type": "text", "text": "🗑️ Full database reset done."}]}


def add_chat_turn(args: Dict[str, Any]) -> Dict[str, Any]:
    """Speichert einen Chat-Turn in der aktuellen Session."""
    ctx = AgentContext.current()
    role = args.get("role", "").strip()
    content = args.get("content", "").strip()

    if not role or not content:
        return {"content": [{"type": "text", "text": "Error: role and content are required"}], "isError": True}

    if role not in ("user", "assistant"):
        return {"content": [{"type": "text", "text": "Error: role must be 'user' or 'assistant'"}], "isError": True}

    add_message(ctx.session_id, role, content)
    return {"content": [{"type": "text", "text": "✅ Chat turn saved."}]}


def _get_db_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn