#!/usr/bin/env python3
"""
memory_panel.py - Memory Panel Komponente
"""

import gradio as gr
from .mcp_client import call_mcp_tool


def get_memories():
    return call_mcp_tool("list_memories", {})


def clear_memory():
    return call_mcp_tool("clear_memory", {})


def get_chat_history():
    return call_mcp_tool("list_chat_history", {"limit": 20})


def clear_chat_history():
    return call_mcp_tool("clear_chat_history", {})


def full_reset():
    return call_mcp_tool("full_reset", {})


def create_memory_panel():
    with gr.Accordion("🧠 Memory", open=True, elem_classes=["panel"]):
        memory_box = gr.Textbox(
            lines=8,
            interactive=False,
            label="Memory Output",
            show_label=False,
            elem_id="memory_box",
            elem_classes=["panel"]
        )

        gr.Markdown("**Long-term Memory**")
        with gr.Row():
            show_lt_btn = gr.Button("Show LT-Memory", size="sm")
            clear_lt_btn = gr.Button("Clear LT-Memory", size="sm", variant="stop")

        with gr.Row():
            memory_search_input = gr.Textbox(
                placeholder="Search memory...",
                scale=5,
                container=False,
                lines=1
            )

        search_memory_btn = gr.Button("Search", size="sm", scale=1)

        gr.Markdown("**Chat History**")
        with gr.Row():
            show_chat_btn = gr.Button("Show Chat-Memory", size="sm")
            clear_chat_btn = gr.Button("Clear Chat-Memory", size="sm", variant="stop")

        gr.Markdown("**Danger Zone**")
        full_reset_btn = gr.Button("🗑️ Full Reset (Nuclear)", size="lg", variant="stop")

    return (
        memory_box,
        show_lt_btn,
        clear_lt_btn,
        show_chat_btn,
        clear_chat_btn,
        full_reset_btn,
        memory_search_input,
        search_memory_btn         
    )


def search_long_term_memory(query: str):
    """Sucht in Long-Term Memory + Chat History (hybride Suche)."""
    q = (query or "").strip().lower()
    if not q:
        return "⚠️ Bitte einen Suchbegriff eingeben."

    results = []

    try:
        # === 1. Long-Term Memory durchsuchen ===
        lt_result = call_mcp_tool("recall_memory", {"query": query.strip(), "limit": 10})

        if lt_result and not lt_result.startswith("Error") and "No relevant memories found" not in lt_result:
            results.append("**🧠 Long-term Memory:**\n" + lt_result)
        else:
            # Keyword-Fallback auf alle Long-Term Memories
            all_lt = call_mcp_tool("list_memories", {})
            if all_lt and not all_lt.startswith("Error"):
                matches = [line for line in all_lt.split("\n") if q in line.lower()]
                if matches:
                    results.append("**🧠 Long-term Memory (erweitert):**\n" + "\n".join(matches[:10]))

        # === 2. Chat History durchsuchen (wenn gewünscht) ===
        chat_result = call_mcp_tool("list_chat_history", {"limit": 60, "format": "text"})

        if chat_result and not chat_result.startswith("Error") and "No chat history" not in chat_result:
            chat_lines = chat_result.split("\n")
            chat_matches = [line for line in chat_lines if q in line.lower()]
            if chat_matches:
                # Nur die relevantesten / letzten Matches nehmen
                results.append("**💬 Chat History:**\n" + "\n".join(chat_matches[-15:]))

        # === Ergebnis zusammenbauen ===
        if results:
            return "\n\n".join(results)
        else:
            return f"🔍 Keine Treffer zu „{query.strip()}“ in Long-Term Memory oder Chat History gefunden."

    except Exception as e:
        return f"❌ Fehler bei der Suche:\n{str(e)}"