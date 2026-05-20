#!/usr/bin/env python3
"""
event_wiring.py - Zentrale Event-Wiring-Schicht für das Frontend

Extrahiert alle .click(), .then(), .submit() und .load() Verbindungen
aus layout.py. Dadurch bleibt layout.py übersichtlich und fokussiert
auf die reine UI-Komposition.

Alle Funktionen sind reine Side-Effect-Funktionen (kein Return-Wert).
"""

import gradio as gr

# === Handler Imports (nur für Wiring) ===
from components.prompt_viewer import get_system_prompt
from components.chat_handler import respond, get_status

# Persona
from components.persona_control import (
    apply_persona,
    reset_persona,
    load_initial_personas,
)

# Skill
from components.skill_control import (
    apply_skill,
    reset_skill,
    load_initial_skills,
)

# Tools
from components.tools_panel import (
    get_tool_names,
    update_tool_info,
    insert_tool,
)

# Memory
from components.memory_panel import (
    get_memories,
    clear_memory,
    get_chat_history,
    clear_chat_history,
    full_reset,
)


def wire_persona_controls(
    persona_dropdown,
    intensity_slider,
    apply_btn,
    reset_btn,
    load_btn,
    model_choice,
    system_prompt_box,
    conn_status,
    prompt_version,
    active_persona,
    active_skill,
):
    """Verdrahtet alle Persona-Controls."""
    apply_btn.click(
        apply_persona,
        inputs=[persona_dropdown, intensity_slider]
    ).then(
        get_system_prompt,
        inputs=[model_choice],
        outputs=[system_prompt_box]
    ).then(
        get_status,
        outputs=[conn_status, prompt_version, active_persona, active_skill]
    )

    reset_btn.click(
        reset_persona
    ).then(
        get_system_prompt,
        inputs=[model_choice],
        outputs=[system_prompt_box]
    ).then(
        get_status,
        outputs=[conn_status, prompt_version, active_persona, active_skill]
    ).then(
        lambda: "Default",
        outputs=[persona_dropdown]
    )

    load_btn.click(
        load_initial_personas,
        outputs=[persona_dropdown]
    )


def wire_skill_controls(
    skill_dropdown,
    apply_skill_btn,
    reset_skill_btn,
    load_skills_btn,
    model_choice,
    system_prompt_box,
    conn_status,
    prompt_version,
    active_persona,
    active_skill,
):
    """Verdrahtet alle Skill-Controls."""
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


def wire_tools_panel(
    tool_dropdown,
    tool_info,
    refresh_btn,
    insert_tool_btn,
    msg,
):
    """Verdrahtet das Tools-Panel (Dropdown + Buttons)."""
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


def wire_memory_panel(
    memory_box,
    show_lt_btn,
    clear_lt_btn,
    show_chat_btn,
    clear_chat_btn,
    full_reset_btn,
):
    """Verdrahtet das Memory-Panel."""
    show_lt_btn.click(get_memories, outputs=[memory_box])
    clear_lt_btn.click(clear_memory, outputs=[memory_box])

    show_chat_btn.click(get_chat_history, outputs=[memory_box])
    clear_chat_btn.click(clear_chat_history, outputs=[memory_box])

    full_reset_btn.click(full_reset, outputs=[memory_box])


def wire_chat_events(
    send_btn,
    msg,
    chatbot,
    model_choice,
    conn_status,
    prompt_version,
    active_persona,
    active_skill,
):
    """Verdrahtet Chat-Events (Send-Button + Enter)."""
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


def wire_initial_demo_loads(
    demo,
    conn_status,
    prompt_version,
    active_persona,
    active_skill,
    system_prompt_box,
    model_choice,
    persona_dropdown,
    skill_dropdown,
    tool_dropdown,
):
    """Verdrahtet alle demo.load() und model_change Events."""
    demo.load(get_status, outputs=[conn_status, prompt_version, active_persona, active_skill])
    demo.load(get_system_prompt, inputs=[model_choice], outputs=[system_prompt_box])
    demo.load(load_initial_personas, outputs=[persona_dropdown])
    demo.load(load_initial_skills, outputs=[skill_dropdown])
    demo.load(get_tool_names, outputs=[tool_dropdown])

    model_choice.change(get_system_prompt, inputs=[model_choice], outputs=[system_prompt_box])