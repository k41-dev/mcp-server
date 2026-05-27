#!/usr/bin/env python3
"""
layout.py - Zentrale UI-Layout-Datei (professionell modularisiert)

Enthält nur noch die reine Zusammenstellung der UI.
Alle Event-Wiring ist ausgelagert in event_wiring.py.
Kein Backend-Import, keine toten Imports, keine Redundanzen.
"""

import gradio as gr
import json

# === Zentrale Refresh-Funktion ===
from .chat_handler import refresh_ui_state, respond, switch_model_provider
from components.memory_panel import get_chat_history
from components.mcp_client import call_mcp_tool

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

from components.sessions_panel import (
    get_session_choices,
    update_session_info,
    switch_to_selected_session,
)


def sync_dropdown_to_active_state(component: str):
    """
    Setzt ein Dropdown (Persona oder Skill) auf den aktuell aktiven Wert der Session.
    
    Args:
        component: "persona" oder "skill"
    """
    if component == "persona":
        tool_name = "get_active_persona"
        default_value = "Default"
    elif component == "skill":
        tool_name = "get_active_skill"
        default_value = "None"
    else:
        return gr.update()

    result = call_mcp_tool(tool_name, {})
    if isinstance(result, str):
        try:
            data = json.loads(result)
            if isinstance(data, dict) and "name" in data:
                return gr.update(value=data["name"])
        except Exception:
            pass

    return gr.update(value=default_value)


def refresh_after_session_switch(model_choice):
    """
    Zentrale Refresh-Funktion nach einem Session-Wechsel.
    Aktualisiert Status, Prompt, Dropdowns und Memory Box.
    """
    # 1. Status Bar + System Prompt + aktive Texte (Persona/Skill)
    status_updates = refresh_after_state_change(model_choice)

    # 2. Persona Dropdown auf den in der Session gespeicherten Wert setzen
    persona_update = sync_dropdown_to_active_state("persona")

    # 3. Skill Dropdown auf den in der Session gespeicherten Wert setzen
    skill_update = sync_dropdown_to_active_state("skill")

    # 4. Memory Box mit Chat History der neuen Session
    memory_update = get_chat_history()

    return status_updates + (persona_update, skill_update, memory_update)


# ====================== CREATE SESSION ======================
def create_and_switch_to_new_session(name: str):
    """Erstellt eine neue Session, wechselt automatisch dorthin und aktualisiert das Dropdown korrekt."""
    name = name.strip() if name else None

    # 1. Session erstellen
    result = call_mcp_tool("create_session", {"name": name} if name else {})

    if isinstance(result, str) and "Error" in result:
        return result, gr.update()

    # 2. Sessions neu laden
    sessions_json = call_mcp_tool("list_sessions", {})
    new_session_id = None
    new_choices = get_session_choices()

    if isinstance(sessions_json, str):
        try:
            session_list = json.loads(sessions_json)
            if session_list:
                new_session_id = session_list[0]["session_id"]
        except Exception:
            pass

    if new_session_id:
        # Direkt zur neuen Session wechseln
        call_mcp_tool("switch_session", {"session_id": new_session_id})

        # Korrekten Choice-String für die neue Session finden
        new_value = None
        for choice in new_choices:
            if str(choice).startswith(f"{new_session_id} —"):
                new_value = choice
                break

        return result, gr.update(choices=new_choices, value=new_value)

    return result, gr.update(choices=new_choices)


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

        # Nach dem Setzen des Providers auch den aktuellen Context in die Session speichern,
        # damit zukünftige Session-Wechsel den Provider mitnehmen.
        try:
            call_mcp_tool("save_current_context", {})
        except:
            pass

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
    persona_dropdown,      
    skill_dropdown,
    memory_box,
    new_session_name,
    create_session_btn,        
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
        # Sicherstellen, dass das Dropdown den ausgewählten Wert auch visuell anzeigt
        lambda selected_session: gr.update(value=selected_session),
        inputs=[session_dropdown],
        outputs=[session_dropdown]
    ).then(
        refresh_after_session_switch,
        inputs=[model_choice],
        outputs=[
            conn_status,
            prompt_version,
            active_persona,
            active_skill,
            current_session,
            model_choice,
            system_prompt_box,
            persona_dropdown,
            skill_dropdown,
            memory_box
        ]
    )

    # === NEU: Session erstellen ===
    def create_new_session(name):
        name = name.strip() if name else None
        result = call_mcp_tool("create_session", {"name": name} if name else {})
        return result

    create_session_btn.click(
        fn=create_and_switch_to_new_session,
        inputs=[new_session_name],
        outputs=[session_info, session_dropdown]
    ).then(
        refresh_after_session_switch,
        inputs=[model_choice],
        outputs=[
            conn_status,
            prompt_version,
            active_persona,
            active_skill,
            current_session,
            model_choice,
            system_prompt_box,
            persona_dropdown,
            skill_dropdown,
            memory_box
        ]
    ).then(
        lambda: "",   # Namensfeld leeren
        outputs=[new_session_name]
    )