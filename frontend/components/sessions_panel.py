#!/usr/bin/env python3
"""
sessions_panel.py - Sessions Panel Komponente
"""

import gradio as gr
import json
from .mcp_client import call_mcp_tool


def get_session_choices():
    """Holt alle Sessions und gibt eine Liste für das Dropdown zurück."""
    try:
        result = call_mcp_tool("list_sessions", {})
        if not result or result.startswith("Error") or result == "[]":
            return ["Keine Sessions gefunden"]

        # JSON parsen
        sessions = json.loads(result)

        choices = []
        for s in sessions:
            sid = s.get("session_id")
            name = s.get("name", f"Session {sid}")
            choices.append(f"{sid} — {name}")

        return choices if choices else ["Keine Sessions gefunden"]

    except Exception as e:
        print(f"[get_session_choices] Fehler: {e}")
        return ["Fehler beim Laden der Sessions"]


def update_session_info(selected_session: str):
    """Zeigt Infos zur ausgewählten Session an."""
    if not selected_session or "—" not in selected_session:
        return "Bitte eine Session auswählen."

    try:
        session_id = int(selected_session.split("—")[0].strip())
        result = call_mcp_tool("get_session", {"session_id": session_id})
        return result
    except Exception as e:
        return f"Fehler: {str(e)}"


def switch_to_selected_session(selected_session: str):
    """Wechselt zur ausgewählten Session."""
    if not selected_session or "—" not in selected_session:
        return "Bitte eine Session auswählen."

    try:
        session_id = int(selected_session.split("—")[0].strip())
        result = call_mcp_tool("switch_session", {"session_id": session_id})
        return result
    except Exception as e:
        return f"Fehler beim Wechseln: {str(e)}"


def create_sessions_panel():
    """Erzeugt das komplette Sessions-Panel."""
    with gr.Accordion("📍 Sessions", open=False, elem_classes=["panel"]):
        session_dropdown = gr.Dropdown(
            label="Select Session",
            choices=get_session_choices(),
            interactive=True
        )

        session_info = gr.Textbox(
            label="Session Details",
            interactive=False,
            lines=4
        )

        with gr.Row():
            refresh_btn = gr.Button("🔄 Refresh Sessions", size="sm")
            switch_btn = gr.Button("Switch to Session", variant="primary", size="sm")

    # Event Wiring (wird später in event_wiring.py zentralisiert)
    session_dropdown.change(
        fn=update_session_info,
        inputs=[session_dropdown],
        outputs=[session_info]
    )

    refresh_btn.click(
        fn=lambda: gr.update(choices=get_session_choices()),
        outputs=[session_dropdown]
    )

    return session_dropdown, session_info, refresh_btn, switch_btn