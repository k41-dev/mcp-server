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
        show_lt_btn, clear_lt_btn,
        show_chat_btn, clear_chat_btn,
        full_reset_btn
    )


def search_long_term_memory(query: str):
    """Sucht im Long-Term Memory und gibt Ergebnisse zurück."""
    if not query or not query.strip():
        return "Bitte einen Suchbegriff eingeben."
    return call_mcp_tool("recall_memory", {"query": query.strip(), "limit": 15})