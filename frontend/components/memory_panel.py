#!/usr/bin/env python3
"""
memory_panel.py - Memory Panel Komponente
"""

import gradio as gr


def get_memories():
    from gradio_app import call_mcp_tool
    return call_mcp_tool("list_memories", {})


def clear_memory():
    from gradio_app import call_mcp_tool
    return call_mcp_tool("clear_memory", {})


def get_chat_history():
    from gradio_app import call_mcp_tool
    return call_mcp_tool("list_chat_history", {"limit": 20})


def clear_chat_history():
    from gradio_app import call_mcp_tool
    return call_mcp_tool("clear_chat_history", {})


def full_reset():
    from gradio_app import call_mcp_tool
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