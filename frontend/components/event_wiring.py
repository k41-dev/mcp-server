#!/usr/bin/env python3
"""
layout.py - Zentrale UI-Layout-Datei (professionell modularisiert)

Enthält nur noch die reine Zusammenstellung der UI.
Alle Event-Wiring ist ausgelagert in event_wiring.py.
Kein Backend-Import, keine toten Imports, keine Redundanzen.
"""

import gradio as gr
import json
import re

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
    status_updates = refresh_after_state_change(model_choice)
    persona_update = sync_dropdown_to_active_state("persona")
    skill_update = sync_dropdown_to_active_state("skill")
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


def delete_session_by_input(name_or_id: str):
    """Löscht eine Session. 
    Wenn die gelöschte Session die aktuell aktive war, wird automatisch zur Default-Session gewechselt."""
    val = (name_or_id or "").strip()
    if not val:
        return "❌ Bitte Session-ID oder Namen eingeben.", gr.update()

    session_id = None

    # ID oder Name auflösen
    try:
        session_id = int(val)
    except ValueError:
        try:
            sessions_json = call_mcp_tool("list_sessions", {})
            if isinstance(sessions_json, str):
                session_list = json.loads(sessions_json)
                for s in session_list:
                    if s.get("name", "").lower() == val.lower():
                        session_id = s["session_id"]
                        break
        except Exception:
            pass

    if session_id is None:
        return f"❌ Session '{val}' nicht gefunden.", gr.update()

    # Aktuell aktive Session ermitteln (bevor wir löschen)
    current_active_id = None
    try:
        active_result = call_mcp_tool("get_active_session", {})
        if isinstance(active_result, str):
            active_data = json.loads(active_result)
            current_active_id = active_data.get("session_id")
    except Exception:
        pass

    # Session löschen
    result = call_mcp_tool("delete_session", {"session_id": session_id})

    # Prüfen, ob wir die aktive Session gelöscht haben
    deleted_active_session = (session_id == current_active_id)

    if deleted_active_session:
        # Zur Default-Session wechseln
        try:
            # Default-Session ist normalerweise ID 1
            call_mcp_tool("switch_session", {"session_id": 1})
        except Exception:
            pass

    # Dropdown neu laden
    new_choices = get_session_choices()

    # Rückgabe: Message + aktualisiertes Dropdown
    # (den vollständigen Refresh machen wir im Wiring)
    return result, gr.update(choices=new_choices)


def refresh_after_state_change(model_choice):
    return refresh_ui_state(model_choice)


def load_chat_history_for_current_session():
    from .mcp_client import call_mcp_tool
    from .chat_handler import _build_response_header
    import json
    import re

    result = call_mcp_tool("list_chat_history", {"limit": 60, "format": "gradio"})

    if isinstance(result, str):
        try:
            data = json.loads(result)
            if isinstance(data, list):
                cleaned = []
                full_header = _build_response_header()
                is_first_assistant_after_user = True

                for msg in data:
                    if msg.get("role") == "user":
                        is_first_assistant_after_user = True
                        cleaned.append(msg)

                    elif msg.get("role") == "tool":
                        cleaned.append({
                            "role": "assistant",
                            "content": "[Tool result received]"
                        })

                    elif msg.get("role") == "assistant":
                        content = str(msg.get("content", "")).strip()

                        if is_first_assistant_after_user:
                            # Nur die erste Assistant-Nachricht nach einem User-Input bekommt den Header
                            lines = content.split("\n")
                            start = 0

                            if lines and lines[0].strip().startswith("**"):
                                start = 1
                                # Verbesserte Erkennung der Context-Zeile (auch neue Varianten)
                                if len(lines) > 1 and any(
                                    x in lines[1] for x in ["🎭", "🛠️", "📍", "•", "Session"]
                                ):
                                    start = 2

                            cleaned_content = "\n".join(lines[start:]).strip()
                            final_content = f"{full_header}\n\n{cleaned_content}".strip() if cleaned_content else full_header
                            is_first_assistant_after_user = False
                        else:
                            # Alle weiteren Assistant-Nachrichten im gleichen Turn bekommen keinen neuen Header
                            final_content = content

                        cleaned.append({
                            "role": "assistant",
                            "content": final_content
                        })
                    else:
                        cleaned.append(msg)

                return cleaned
        except Exception:
            pass
    return []


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
    memory_search_input,      
    search_memory_btn,        
):
    """Verdrahtet das Memory-Panel."""
    show_lt_btn.click(get_memories, outputs=[memory_box])
    clear_lt_btn.click(clear_memory, outputs=[memory_box])

    show_chat_btn.click(get_chat_history, outputs=[memory_box])
    clear_chat_btn.click(clear_chat_history, outputs=[memory_box])

    full_reset_btn.click(full_reset, outputs=[memory_box])

    # === NEU: Memory Search ===
    search_memory_btn.click(
        search_long_term_memory,
        inputs=[memory_search_input],
        outputs=[memory_box]
    )


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
    chatbot,
    memory_box,
):
    """Verdrahtet alle demo.load() und model_change Events."""

    # === Inner Function (wichtig!) ===
    def on_model_change(model_choice_value: str):
        switch_model_provider(model_choice_value)

        try:
            call_mcp_tool("save_current_context", {})
        except:
            pass

        return refresh_after_state_change(model_choice_value)

    # === Initial Load ===
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
    ).then(
        load_chat_history_for_current_session,
        outputs=[chatbot]
    ).then(
        get_chat_history,           # ← NEU: Chat History automatisch ins Memory Panel laden
        outputs=[memory_box]
    )

    demo.load(load_initial_personas, outputs=[persona_dropdown])
    demo.load(load_initial_skills, outputs=[skill_dropdown])
    demo.load(get_tool_names, outputs=[tool_dropdown])

    # === Model Change ===
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
    chatbot,
    session_identifier,
    create_session_btn,
    delete_session_btn,        
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
    ).then(
        load_chat_history_for_current_session,
        outputs=[chatbot]         
    ).then(
        get_chat_history,                   
        outputs=[memory_box]
    )

    # === NEU: Session erstellen ===
    def create_new_session(name):
        name = name.strip() if name else None
        result = call_mcp_tool("create_session", {"name": name} if name else {})
        return result

    create_session_btn.click(
        fn=create_and_switch_to_new_session,
        inputs=[session_identifier],
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
        outputs=[session_identifier]
    )

    delete_session_btn.click(
        fn=delete_session_by_input,
        inputs=[session_identifier],
        outputs=[session_info, session_dropdown]
    ).then(
        lambda: "",
        outputs=[session_identifier]
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