#!/usr/bin/env python3
"""
memory.py - Memory Tools
"""

from typing import Dict, Any
from backend.memory import DEFAULT_SESSION_ID


def store_memory(args: Dict[str, Any]) -> Dict[str, Any]:
    from backend.memory import store_long_term_memory
    fact = args.get("fact", "").strip()
    if not fact:
        return {"content": [{"type": "text", "text": "Error: fact is required"}], "isError": True}

    source = args.get("source", "agent")
    mem_id = store_long_term_memory(DEFAULT_SESSION_ID, fact, source)
    return {"content": [{"type": "text", "text": f"✅ Memory stored (id={mem_id})"}]}


def recall_memory(args: Dict[str, Any]) -> Dict[str, Any]:
    from backend.memory import recall_memories
    query = args.get("query", "")
    limit = args.get("limit", 8)

    memories = recall_memories(DEFAULT_SESSION_ID, query, limit)
    if not memories:
        return {"content": [{"type": "text", "text": "No relevant memories found."}]}

    text = "\n".join([f"• {m['fact']}" for m in memories])
    return {"content": [{"type": "text", "text": text}]}


def list_memories(args: Dict[str, Any]) -> Dict[str, Any]:
    from backend.memory import list_all_memories
    memories = list_all_memories(DEFAULT_SESSION_ID)
    if not memories:
        return {"content": [{"type": "text", "text": "No memories stored yet."}]}

    text = "\n".join([f"• {m['fact']}" for m in memories])
    return {"content": [{"type": "text", "text": text}]}


def clear_memory(args: Dict[str, Any]) -> Dict[str, Any]:
    from backend.memory import clear_long_term_memory
    clear_long_term_memory()
    return {"content": [{"type": "text", "text": "🗑️ Long-term memory cleared."}]}


def clear_chat_history(args: Dict[str, Any]) -> Dict[str, Any]:
    from backend.memory import clear_chat_history as _clear_chat
    _clear_chat()
    return {"content": [{"type": "text", "text": "🗑️ Chat history cleared."}]}


def list_chat_history(args: Dict[str, Any]) -> Dict[str, Any]:
    from backend.memory import get_recent_messages
    limit = args.get("limit", 20)
    messages = get_recent_messages(DEFAULT_SESSION_ID, limit)
    
    if not messages:
        return {"content": [{"type": "text", "text": "No chat history."}]}
    
    text = "\n".join([f"{m['role']}: {m['content'][:120]}" for m in messages])
    return {"content": [{"type": "text", "text": text}]}


def full_reset(args: Dict[str, Any]) -> Dict[str, Any]:
    from backend.memory import full_reset as _full_reset
    _full_reset()
    return {"content": [{"type": "text", "text": "🗑️ Full database reset done."}]}


def add_chat_turn(args: Dict[str, Any]) -> Dict[str, Any]:
    from backend.memory import add_message
    
    role = args.get("role", "").strip()
    content = args.get("content", "").strip()
    
    if not role or not content:
        return {"content": [{"type": "text", "text": "Error: role and content are required"}], "isError": True}
    
    if role not in ("user", "assistant"):
        return {"content": [{"type": "text", "text": "Error: role must be 'user' or 'assistant'"}], "isError": True}
    
    add_message(DEFAULT_SESSION_ID, role, content)
    return {"content": [{"type": "text", "text": "✅ Chat turn saved."}]}