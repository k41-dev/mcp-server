#!/usr/bin/env python3
"""
layout.py - Zentrale UI-Layout-Datei (professionell modularisiert)

Enthält nur noch die reine Zusammenstellung der UI.
Alle Event-Wiring ist ausgelagert in event_wiring.py.
Kein Backend-Import, keine toten Imports, keine Redundanzen.
"""

import gradio as gr

# === Zentrale Refresh-Funktion ===
from .chat_handler import refresh_ui_state, respond, switch_model_provider

# === Handler Imports ===
from components.persona_control import (
    apply_persona,
    reset_persona,
    load_initial_personas,
)

from components.skill_control import (
    apply_skill,
    reset_skill,
    load_initial_skills,
)

from components.tools_panel import (
    get_tool_names,
    update_tool_info,
    insert_tool,
)

from components.memory_panel import (
    get_memories,
    clear_memory,
    get_chat_history,
    clear_chat_history,
    full_reset,
)


def refresh_after_state_change(model_choice):
    return refresh_ui_state(model_choice)


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
    current_session,          # ← neu hinzugefügt
):
    """Verdrahtet alle Persona-Controls."""
    apply_btn.click(
        apply_persona,
        inputs=[persona_dropdown, intensity_slider]
    ).then(
        refresh_after_state_change,
        inputs=[model_choice],
        outputs=[
            conn_status,
            prompt_version,
            active_persona,
            active_skill,
            current_session,
            model_choice,
            system_prompt_box
        ]
    )

    reset_btn.click(
        reset_persona
    ).then(
        refresh_after_state_change,
        inputs=[model_choice],
        outputs=[
            conn_status,
            prompt_version,
            active_persona,
            active_skill,
            current_session,
            model_choice,
            system_prompt_box
        ]
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
    current_session,          # ← neu hinzugefügt
):
    """Verdrahtet alle Skill-Controls."""
    apply_skill_btn.click(
        apply_skill,
        inputs=[skill_dropdown]
    ).then(
        refresh_after_state_change,
        inputs=[model_choice],
        outputs=[
            conn_status,
            prompt_version,
            active_persona,
            active_skill,
            current_session,
            model_choice,
            system_prompt_box
        ]
    )

    reset_skill_btn.click(
        reset_skill
    ).then(
        refresh_after_state_change,
        inputs=[model_choice],
        outputs=[
            conn_status,
            prompt_version,
            active_persona,
            active_skill,
            current_session,
            model_choice,
            system_prompt_box
        ]
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
    system_prompt_box,
    current_session,          # ← neu hinzugefügt
):
    """Verdrahtet Chat-Events (Send-Button + Enter).

    Verwendet refresh_ui_state, damit Status-Bar und System Prompt Viewer
    nach dem Senden einer Nachricht synchron bleiben (auch bei Ollama).
    """
    send_btn.click(
        respond,
        [msg, chatbot, model_choice],
        [chatbot, msg]
    ).then(
        refresh_after_state_change,
        inputs=[model_choice],
        outputs=[
            conn_status,
            prompt_version,
            active_persona,
            active_skill,
            current_session,
            model_choice,
            system_prompt_box
        ]
    )

    msg.submit(
        respond,
        [msg, chatbot, model_choice],
        [chatbot, msg]
    ).then(
        refresh_after_state_change,
        inputs=[model_choice],
        outputs=[
            conn_status,
            prompt_version,
            active_persona,
            active_skill,
            current_session,
            model_choice,
            system_prompt_box
        ]
    )


def wire_initial_demo_loads(
    demo,
    conn_status,
    prompt_version,
    active_persona,
    active_skill,
    current_session,
    system_prompt_box,
    model_choice,
    persona_dropdown,
    skill_dropdown,
    tool_dropdown,
):
    """Verdrahtet alle demo.load() und model_change Events.

    Verwendet die zentrale refresh_after_state_change Funktion, damit
    Status-Bar und System Prompt Viewer immer synchron aktualisiert werden.
    """
    # Initial Load: Ein einziger Aufruf für Status + Prompt
    demo.load(
        refresh_after_state_change,
        inputs=[model_choice],
        outputs=[
            conn_status,
            prompt_version,
            active_persona,
            active_skill,
            current_session,
            model_choice,
            system_prompt_box
        ]
    )
    demo.load(load_initial_personas, outputs=[persona_dropdown])
    demo.load(load_initial_skills, outputs=[skill_dropdown])
    demo.load(get_tool_names, outputs=[tool_dropdown])

    def on_model_change(model_choice_value: str):
        switch_model_provider(model_choice_value)
        return refresh_after_state_change(model_choice_value)

    # Model-Wechsel: Zentrale Funktion statt .then()-Kette
    model_choice.change(
        on_model_change,
        inputs=[model_choice],
        outputs=[
            conn_status,
            prompt_version,
            active_persona,
            active_skill,
            current_session,
            model_choice,
            system_prompt_box
        ]
    )


# ====================== SESSIONS PANEL ======================
from components.sessions_panel import (
    get_session_choices,
    update_session_info,
    switch_to_selected_session,
)


def wire_sessions_panel(
    session_dropdown,
    session_info,
    refresh_btn,
    switch_btn,
    model_choice,
    conn_status,
    prompt_version,
    active_persona,
    active_skill,
    current_session,
    system_prompt_box,
    persona_dropdown,      # ← neu
    skill_dropdown,        # ← neu
):
    """Verdrahtet das Sessions-Panel mit automatischer Status-Aktualisierung."""

    from components.persona_control import load_initial_personas
    from components.skill_control import load_initial_skills

    # Session auswählen → Details anzeigen
    session_dropdown.change(
        fn=update_session_info,
        inputs=[session_dropdown],
        outputs=[session_info]
    )

    # Sessions neu laden
    def refresh_session_list():
        new_choices = get_session_choices()
        return gr.update(choices=new_choices)

    refresh_btn.click(
        fn=refresh_session_list,
        outputs=[session_dropdown]
    )

    # Session wechseln + danach kompletten UI-Status + Dropdowns aktualisieren
    switch_btn.click(
        fn=switch_to_selected_session,
        inputs=[session_dropdown],
        outputs=[session_info]
    ).then(
        refresh_after_state_change,
        inputs=[model_choice],
        outputs=[
            conn_status,
            prompt_version,
            active_persona,
            active_skill,
            current_session,
            model_choice,
            system_prompt_box
        ]
    ).then(
        lambda: gr.update(value="Default"),
        outputs=[persona_dropdown]
    ).then(
        lambda: gr.update(value="None"),
        outputs=[skill_dropdown]
    ).then(
        load_initial_personas,
        outputs=[persona_dropdown]
    ).then(
        load_initial_skills,
        outputs=[skill_dropdown]
    )