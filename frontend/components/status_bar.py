#!/usr/bin/env python3
"""
status_bar.py - Interaktive Status-Bar / Navbar Komponente

Enthält:
- Connection Status
- Prompt Version (mit Rebuild-Button)
- Active Persona
- Active Skill
- Model Selector (Grok / Ollama)

Diese Komponente wird später zur vollwertigen Navbar ausgebaut.
Alle Aktionen laufen über MCP JSON-RPC.
"""

import gradio as gr
from typing import Tuple


def create_status_bar() -> Tuple[gr.Textbox, gr.Textbox, gr.Textbox, gr.Textbox, gr.Radio]:
    """
    Erzeugt die obere Status-Bar (zukünftige Navbar).

    Returns:
        (conn_status, prompt_version, active_persona, active_skill, model_choice)
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
            ["Grok", "Ollama"],
            value="Grok",
            label="Model",
            interactive=True,
            scale=1.5
        )

    return conn_status, prompt_version, active_persona, active_skill, model_choice
