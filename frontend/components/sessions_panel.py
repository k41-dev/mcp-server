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
        new_session_name,           # ← neu
        create_session_btn          # ← neu
    )