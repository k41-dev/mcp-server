#!/usr/bin/env python3
"""
persona_control.py - Persona Control Komponente
"""

import gradio as gr
import json


def get_persona_choices():
    """Returns a clean list of personas for the dropdown."""
    try:
        from gradio_app import call_mcp_tool
        result = call_mcp_tool("list_personas", {})
        if isinstance(result, str):
            try:
                data = json.loads(result)
                if isinstance(data, list):
                    names = ["default"] + [item.get("name", "").lower() for item in data if item.get("name")]
                    return [n for n in names if n]
            except Exception:
                pass
    except Exception as e:
        print(f"[ERROR] get_persona_choices failed: {e}")
    return ["Default"]


def apply_persona(persona_name: str, intensity: int):
    if not persona_name or persona_name.lower() == "default":
        return "Please select a persona first."

    from gradio_app import call_mcp_tool
    result = call_mcp_tool("set_active_persona", {
        "persona_name": persona_name,
        "intensity": int(intensity)
    })

    if isinstance(result, str) and ("Error" in result or "error" in result.lower()):
        return f"❌ Fehler beim Aktivieren von '{persona_name}': {result}"

    return f"✅ {persona_name}"


def reset_persona():
    from gradio_app import call_mcp_tool
    call_mcp_tool("clear_active_persona", {})
    return "Default"


def load_initial_personas():
    choices = get_persona_choices()
    normalized = [c.lower() for c in choices]
    
    if "default" not in normalized:
        choices = ["Default"] + choices
    else:
        choices = ["Default"] + [c for c in choices if c.lower() != "default"]
    
    return gr.update(choices=choices, value="Default")


def create_persona_control():
    """Erzeugt die komplette Persona Control Accordion."""
    with gr.Accordion("🎭 Persona", open=False, elem_classes=["panel"]):
        persona_dropdown = gr.Dropdown(
            label="Select Persona",
            choices=get_persona_choices(),
            interactive=True
        )
        intensity_slider = gr.Slider(1, 10, value=7, step=1, label="Intensity")

        with gr.Row():
            apply_btn = gr.Button("Apply Persona", variant="primary", size="sm")
            reset_btn = gr.Button("Reset Persona", variant="stop", size="sm")

        load_btn = gr.Button("🔄 Load Personas", size="sm")

    return persona_dropdown, intensity_slider, apply_btn, reset_btn, load_btn