#!/usr/bin/env python3
"""
skill_control.py - Skill Control Komponente
"""

import gradio as gr
import json


def get_skill_choices():
    """Returns a clean list of skills for the dropdown."""
    try:
        from gradio_app import call_mcp_tool
        result = call_mcp_tool("list_skills", {})
        
        if not isinstance(result, str):
            return []

        start = result.find("[")
        end = result.rfind("]") + 1

        if start == -1 or end == 0:
            return []

        json_part = result[start:end]
        data = json.loads(json_part)

        if isinstance(data, list):
            names = [
                item.get("name", "").lower().strip()
                for item in data
                if item.get("name")
            ]
            return sorted(set(names))

        return []

    except Exception as e:
        print(f"[get_skill_choices] Fehler: {e}")
        return []


def apply_skill(skill_name: str):
    if not skill_name or skill_name == "None":
        return "Please select a skill first."

    from gradio_app import call_mcp_tool
    result = call_mcp_tool("execute_skill", {
        "skill_name": skill_name
    })

    if isinstance(result, str) and ("Error" in result or "error" in result.lower()):
        return f"❌ Fehler beim Aktivieren von '{skill_name}': {result}"

    return f"✅ Skill aktiviert: {skill_name}"


def reset_skill():
    from gradio_app import call_mcp_tool
    call_mcp_tool("clear_active_skill", {})
    return "None"


def load_initial_skills():
    choices = get_skill_choices()
    
    if "None" not in [c.lower() for c in choices]:
        choices = ["None"] + choices
    else:
        choices = ["None"] + [c for c in choices if c.lower() != "none"]
    
    return gr.update(choices=choices, value="None")


def create_skill_control():
    """Erzeugt die komplette Skill Control Accordion."""
    with gr.Accordion("🛠️ Skill", open=False, elem_classes=["panel"]):
        skill_dropdown = gr.Dropdown(
            label="Select Skill",
            choices=get_skill_choices(),
            value="None",
            interactive=True
        )

        with gr.Row():
            apply_skill_btn = gr.Button("Activate Skill", variant="primary", size="sm")
            reset_skill_btn = gr.Button("Reset Skill", variant="stop", size="sm")

        load_skills_btn = gr.Button("🔄 Load Skills", size="sm")

    return skill_dropdown, apply_skill_btn, reset_skill_btn, load_skills_btn