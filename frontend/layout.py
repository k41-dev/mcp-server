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

                def _handle_model_change(model):
                    return gr.update(value=get_system_prompt(model))

                model_choice.change(
                    fn=_handle_model_change,
                    inputs=[model_choice],
                    outputs=[system_prompt_box]
                )

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

                wire_skill_controls(
                    skill_dropdown=skill_dropdown,
                    apply_skill_btn=apply_skill_btn,
                    reset_skill_btn=reset_skill_btn,
                    load_skills_btn=load_skills_btn,
                    model_choice=model_choice,
                    system_prompt_box=system_prompt_box,
                    conn_status=conn_status,
                    prompt_version=prompt_version,
                    active_persona=active_persona,
                    active_skill=active_skill,
                )

                # === Tools Panel ===
                initial_tool_choices = get_tool_names()
                initial_tool_value = initial_tool_choices[0] if initial_tool_choices else None

                tool_dropdown, tool_info, refresh_btn, insert_tool_btn = create_tools_panel(
                    initial_choices=initial_tool_choices,
                    initial_value=initial_tool_value
                )

                # Tools Event Wiring (über event_wiring.py)
                wire_tools_panel(
                    tool_dropdown=tool_dropdown,
                    tool_info=tool_info,
                    refresh_btn=refresh_btn,
                    insert_tool_btn=insert_tool_btn,
                    msg=msg,
                )

                # === Memory Panel ===
                memory_box, show_lt_btn, clear_lt_btn, show_chat_btn, clear_chat_btn, full_reset_btn = create_memory_panel()

                # Memory Event Wiring
                wire_memory_panel(
                    memory_box=memory_box,
                    show_lt_btn=show_lt_btn,
                    clear_lt_btn=clear_lt_btn,
                    show_chat_btn=show_chat_btn,
                    clear_chat_btn=clear_chat_btn,
                    full_reset_btn=full_reset_btn,
                )

        # ====================== CHAT EVENT WIRING ======================
        wire_chat_events(
            send_btn=send_btn,
            msg=msg,
            chatbot=chatbot,
            model_choice=model_choice,
            conn_status=conn_status,
            prompt_version=prompt_version,
            active_persona=active_persona,
            active_skill=active_skill,
        )

        # ====================== INITIAL LOAD & MODEL CHANGE ======================
        wire_initial_demo_loads(
            demo=demo,
            conn_status=conn_status,
            prompt_version=prompt_version,
            active_persona=active_persona,
            active_skill=active_skill,
            system_prompt_box=system_prompt_box,
            model_choice=model_choice,
            persona_dropdown=persona_dropdown,
            skill_dropdown=skill_dropdown,
            tool_dropdown=tool_dropdown,
        )

        def _handle_model_change(model):
            new_prompt = get_system_prompt(model)
            return gr.update(value=new_prompt)

        model_choice.change(
            fn=_handle_model_change,
            inputs=[model_choice],
            outputs=[system_prompt_box]
        )

    return demo
