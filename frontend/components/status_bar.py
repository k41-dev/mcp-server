#!/usr/bin/env python3
"""
status_bar.py - Interaktive Status-Bar / Navbar Komponente
"""

import gradio as gr
from typing import Tuple
from .mcp_client import call_mcp_tool, mcp_jsonrpc


def create_status_bar() -> Tuple[gr.Textbox, gr.Textbox, gr.Textbox, gr.Textbox, gr.Radio]:
    """
    Erzeugt die obere Status-Bar (zukünftige Navbar).
    """
    with gr.Row(
        elem_classes=["panel", "status-bar"],
        equal_height=True
    ):
        conn_status = gr.Textbox(
            value="✅ Connected • 32 tools",
            label="Connection",
            interactive=False,
            scale=2.2
        )
        prompt_version = gr.Textbox(
            value="📜 Prompt: a2fc2d1d8f",
            label="Prompt Version",
            interactive=False,
            scale=1.8
        )
        active_persona = gr.Textbox(
            value="🎭 Persona: None",
            label="Active Persona",
            interactive=False,
            scale=2
        )
        active_skill = gr.Textbox(
            value="🛠️ Skill: None",
            label="Active Skill",
            interactive=False,
            scale=2
        )
        model_choice = gr.Radio(
            ["xAI", "OpenAI", "Anthropic", "Ollama"],
            value="xAI",
            label="Model",
            interactive=True,
            scale=1.5
        )

    return conn_status, prompt_version, active_persona, active_skill, model_choice