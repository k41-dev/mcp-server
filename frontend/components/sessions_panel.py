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

        # Fehlerfälle abfangen
        if not result or result.startswith("Error") or result.strip() == "[]":
            return ["Keine Sessions gefunden"]

        sessions = json.loads(result)

        # Sicherstellen, dass es eine Liste ist
        if not isinstance(sessions, list):
            return ["Fehler: Ungültiges Session-Format"]

        choices = []
        for s in sessions:
            sid = s.get("session_id")
            name = s.get("name") or f"Session {sid}"

            # ID immer als String behandeln für konsistente Formatierung
            choices.append(f"{sid} — {name}")

        return choices if choices else ["Keine Sessions gefunden"]

    except json.JSONDecodeError:
        print("[get_session_choices] JSON konnte nicht geparst werden.")
        return ["Fehler beim Laden der Sessions"]
    except Exception as e:
        print(f"[get_session_choices] Unerwarteter Fehler: {e}")
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
    with gr.Accordion("📍 Sessions", open=False, elem_classes=["panel"]):
        session_dropdown = gr.Dropdown(
            label="Select Session",
            choices=get_session_choices(),
            interactive=True
        )

        session_info = gr.Textbox(
            label="Session Info",
            interactive=False,
            lines=4
        )

        with gr.Row():
            refresh_sessions_btn = gr.Button("🔄 Refresh", size="sm")
            switch_session_btn = gr.Button("Switch Session", size="sm", variant="primary")

        gr.Markdown("**Neue Session erstellen**")
        with gr.Row():
            new_session_name = gr.Textbox(
                label="Session Name (optional)",
                placeholder="z.B. Projekt XY",
                scale=3
            )
            create_session_btn = gr.Button("Create Session", size="sm", variant="secondary")

    return (
        session_dropdown, 
        session_info, 
        refresh_sessions_btn, 
        switch_session_btn,
        new_session_name,          
        create_session_btn          
    )