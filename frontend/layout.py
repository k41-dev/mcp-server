#!/usr/bin/env python3
"""
layout.py - Zentrale UI-Layout-Datei (professionell modularisiert)

Enthält nur noch die reine Zusammenstellung der UI.
Alle Event-Wiring ist ausgelagert in event_wiring.py.
"""

from pathlib import Path
import gradio as gr

# === Komponenten ===
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
from components.sessions_panel import create_sessions_panel

# === Event Wiring ===
from components.event_wiring import (
    wire_persona_controls,
    wire_skill_controls,
    wire_tools_panel,
    wire_memory_panel,
    wire_chat_events,
    wire_initial_demo_loads,
    wire_sessions_panel,
)

from components.tools_panel import get_tool_names


def create_ui():
    """Erstellt die komplette MCP Agent Web UI."""
    css_path = Path(__file__).parent / "style.css"
    custom_css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""

    with gr.Blocks(title="Wäärkzüüg-Chaschte 🧰", css=custom_css) as demo:
        gr.Markdown("# Wäärkzüüg-Chaschte 🧰")

        # ========== TOP STATUS BAR ==========
        conn_status, prompt_version, active_persona, active_skill, current_session, model_choice = create_status_bar()

        # ========== TWO COLUMN LAYOUT ==========
        with gr.Row(elem_classes=["main-layout"]):

            # ========== CHAT PANEL (links) ==========
            chatbot, msg, send_btn = create_chat_panel()

            # ========== RIGHT COLUMN ==========
            with gr.Column(scale=1, elem_classes=["menue-column"]):

                # === System Prompt Viewer ===
                system_prompt_box = create_prompt_viewer()

                # === Persona Control ===
                persona_dropdown, intensity_slider, apply_btn, reset_btn, load_btn = create_persona_control()

                # === Skill Control ===
                skill_dropdown, apply_skill_btn, reset_skill_btn, load_skills_btn = create_skill_control()

                # === Tools Panel ===
                initial_tool_choices = get_tool_names()
                initial_tool_value = initial_tool_choices[0] if initial_tool_choices else None

                tool_dropdown, tool_info, refresh_btn, insert_tool_btn = create_tools_panel(
                    initial_choices=initial_tool_choices,
                    initial_value=initial_tool_value
                )

                # === Sessions Panel ===
                session_dropdown, session_info, refresh_sessions_btn, switch_session_btn, session_identifier, create_session_btn, delete_session_btn = create_sessions_panel()

                # === Memory Panel ===
                memory_box, show_lt_btn, clear_lt_btn, show_chat_btn, clear_chat_btn, full_reset_btn = create_memory_panel()

        # ====================== EVENT WIRING (am Ende) ======================
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
            current_session=current_session,
        )

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
            current_session=current_session,
        )

        wire_tools_panel(
            tool_dropdown=tool_dropdown,
            tool_info=tool_info,
            refresh_btn=refresh_btn,
            insert_tool_btn=insert_tool_btn,
            msg=msg,
        )

        wire_memory_panel(
            memory_box=memory_box,
            show_lt_btn=show_lt_btn,
            clear_lt_btn=clear_lt_btn,
            show_chat_btn=show_chat_btn,
            clear_chat_btn=clear_chat_btn,
            full_reset_btn=full_reset_btn,
        )

        wire_sessions_panel(
            session_dropdown=session_dropdown,
            session_info=session_info,
            refresh_btn=refresh_sessions_btn,
            switch_btn=switch_session_btn,
            model_choice=model_choice,
            conn_status=conn_status,
            prompt_version=prompt_version,
            active_persona=active_persona,
            active_skill=active_skill,
            current_session=current_session,
            system_prompt_box=system_prompt_box,
            persona_dropdown=persona_dropdown,
            skill_dropdown=skill_dropdown,
            memory_box=memory_box,
            chatbot=chatbot,
            session_identifier=session_identifier,       
            create_session_btn=create_session_btn,
            delete_session_btn=delete_session_btn,
        )

        wire_chat_events(
            send_btn=send_btn,
            msg=msg,
            chatbot=chatbot,
            model_choice=model_choice,
            conn_status=conn_status,
            prompt_version=prompt_version,
            active_persona=active_persona,
            active_skill=active_skill,
            system_prompt_box=system_prompt_box,
            current_session=current_session,
        )

        wire_initial_demo_loads(
            demo=demo,
            conn_status=conn_status,
            prompt_version=prompt_version,
            active_persona=active_persona,
            active_skill=active_skill,
            current_session=current_session,
            system_prompt_box=system_prompt_box,
            model_choice=model_choice,
            persona_dropdown=persona_dropdown,
            skill_dropdown=skill_dropdown,
            tool_dropdown=tool_dropdown,
            chatbot=chatbot,
        )

    return demo