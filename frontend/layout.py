#!/usr/bin/env python3
"""
layout.py - Zentrale UI-Layout-Datei (professionell modularisiert)

Enthält die komplette Zusammenstellung der Gradio-Oberfläche.
gradio_app.py wird dadurch zur reinen Einstiegsdatei.
"""

from pathlib import Path
import gradio as gr

# === Komponenten + Handler Funktionen ===
from components import (
    create_status_bar,
    create_prompt_viewer,
    create_persona_control,
    create_skill_control,
    create_tools_panel,
    create_memory_panel,
    create_chat_panel
)

from components.prompt_viewer import get_system_prompt
from components.mcp_client import get_mcp_tools
from components.chat_handler import respond, get_status

# === Event Wiring (neu) ===
from components.event_wiring import (
    wire_persona_controls,
    wire_skill_controls,
    wire_tools_panel,
    wire_memory_panel,
    wire_chat_events,
    wire_initial_demo_loads,
)

# === Temporäre Imports für demo.load() ===
from components.persona_control import load_initial_personas
from components.skill_control import load_initial_skills
from components.tools_panel import get_tool_names

# Skill Control Funktionen
from components.skill_control import (
    apply_skill,
    reset_skill,
    load_initial_skills,
)

# Tools Panel Funktionen
from components.tools_panel import (
    get_tool_names,
    update_tool_info,
    insert_tool,
)

# Memory Panel Funktionen
from components.memory_panel import (
    get_memories,
    clear_memory,
    get_chat_history,
    clear_chat_history,
    full_reset,
)


def create_ui():
    """Erstellt die komplette MCP Agent Web UI."""
    css_path = Path(__file__).parent / "style.css"
    custom_css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""

    with gr.Blocks(title="MCP-Server", css=custom_css) as demo:
        gr.Markdown("# 🚀 MCP-Server")

        # ========== TOP STATUS BAR ==========
        conn_status, prompt_version, active_persona, active_skill, model_choice = create_status_bar()

        # ========== TWO COLUMN LAYOUT ==========
        with gr.Row(elem_classes=["main-layout"]):
            
            # ========== CHAT PANEL (links) ==========
            chatbot, msg, send_btn = create_chat_panel()

            # ========== RIGHT: Menü ==========
            with gr.Column(scale=1, elem_classes=["menue-column"]):

                # === System Prompt Viewer ===
                system_prompt_box = create_prompt_viewer()

                # === Persona Control ===
                persona_dropdown, intensity_slider, apply_btn, reset_btn, load_btn = create_persona_control()

                # === Persona Event Wiring (jetzt über event_wiring.py) ===
                wire_persona_controls(
                    persona_dropdown=persona_dropdown,
                    intensity_slider=intensity_slider,
                    apply_btn=apply_btn,
                    reset_btn=reset_btn,
                    load_btn=load_btn,
                    model_choice=model_choice,
                    system_prompt_box=system_prompt_box,
                    conn_status=conn_status,
                    prompt_version=prompt_version,
                    active_persona=active_persona,
                    active_skill=active_skill,
                )

                # === Skill Control ===
                skill_dropdown, apply_skill_btn, reset_skill_btn, load_skills_btn = create_skill_control()

                # === Skill Event Wiring ===
                apply_skill_btn.click(
                    apply_skill,
                    inputs=[skill_dropdown]
                ).then(
                    get_system_prompt,
                    inputs=[model_choice],
                    outputs=[system_prompt_box]
                ).then(
                    get_status,
                    outputs=[conn_status, prompt_version, active_persona, active_skill]
                )

                reset_skill_btn.click(
                    reset_skill
                ).then(
                    get_system_prompt,
                    inputs=[model_choice],
                    outputs=[system_prompt_box]
                ).then(
                    get_status,
                    outputs=[conn_status, prompt_version, active_persona, active_skill]
                ).then(
                    lambda: "None",
                    outputs=[skill_dropdown]
                )

                load_skills_btn.click(
                    load_initial_skills,
                    outputs=[skill_dropdown]
                )

                # === Tools Panel ===
                initial_tool_choices = get_tool_names()
                initial_tool_value = initial_tool_choices[0] if initial_tool_choices else None

                tool_dropdown, tool_info, refresh_btn, insert_tool_btn = create_tools_panel(
                    initial_choices=initial_tool_choices,
                    initial_value=initial_tool_value
                )

                tool_dropdown.change(
                    fn=update_tool_info,
                    inputs=[tool_dropdown],
                    outputs=[tool_info]
                )

                def refresh_tool_list():
                    new_choices = get_tool_names()
                    new_value = new_choices[0] if new_choices else None
                    return gr.update(choices=new_choices, value=new_value)

                refresh_btn.click(
                    fn=refresh_tool_list,
                    outputs=[tool_dropdown]
                ).then(
                    fn=lambda x: update_tool_info(x) if x else "",
                    inputs=[tool_dropdown],
                    outputs=[tool_info]
                )

                insert_tool_btn.click(
                    fn=insert_tool,
                    inputs=[tool_dropdown, msg],
                    outputs=[msg, tool_dropdown]
                )

                # === Memory Panel ===
                memory_box, show_lt_btn, clear_lt_btn, show_chat_btn, clear_chat_btn, full_reset_btn = create_memory_panel()

                show_lt_btn.click(get_memories, outputs=[memory_box])
                clear_lt_btn.click(clear_memory, outputs=[memory_box])

                show_chat_btn.click(get_chat_history, outputs=[memory_box])
                clear_chat_btn.click(clear_chat_history, outputs=[memory_box])

                full_reset_btn.click(full_reset, outputs=[memory_box])

        # ====================== CHAT EVENT WIRING ======================
        send_btn.click(
            respond, 
            [msg, chatbot, model_choice], 
            [chatbot, msg]
        ).then(
            get_status,
            outputs=[conn_status, prompt_version, active_persona, active_skill]
        )

        msg.submit(
            respond, 
            [msg, chatbot, model_choice], 
            [chatbot, msg]
        ).then(
            get_status,
            outputs=[conn_status, prompt_version, active_persona, active_skill]
        )


        # ====================== DEMO LOAD ======================
        demo.load(get_status, outputs=[conn_status, prompt_version, active_persona, active_skill])
        demo.load(get_system_prompt, inputs=[model_choice], outputs=[system_prompt_box])
        demo.load(load_initial_personas, outputs=[persona_dropdown])
        demo.load(load_initial_skills, outputs=[skill_dropdown])
        demo.load(get_tool_names, outputs=[tool_dropdown])
        
        model_choice.change(get_system_prompt, inputs=[model_choice], outputs=[system_prompt_box])

    return demo
