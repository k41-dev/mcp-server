#!/usr/bin/env python3
"""
tools_panel.py - Tools Panel Komponente (stabile Version - Option 1)
"""

import gradio as gr
from .mcp_client import get_mcp_tools


def get_tool_names():
    try:
        tools = get_mcp_tools()
        if isinstance(tools, list):
            return [t["function"]["name"] for t in tools if isinstance(t, dict) and "function" in t and "name" in t["function"]]
        return []
    except Exception as e:
        print(f"[get_tool_names] Fehler: {e}")
        return []


def update_tool_info(tool_name):
    if isinstance(tool_name, list):
        tool_name = tool_name[0] if tool_name else ""
    
    if not tool_name or not isinstance(tool_name, str):
        return ""
    
    try:
        tools = get_mcp_tools()
        for t in tools:
            if t.get("function", {}).get("name") == tool_name:
                return t.get("function", {}).get("description", "No description available.")
        return "Tool nicht gefunden."
    except Exception as e:
        return f"Error: {str(e)}"


def insert_tool(tool_name, current_msg: str):
    if isinstance(tool_name, list):
        tool_name = tool_name[0] if tool_name else ""
    
    if not tool_name:
        return current_msg or "", tool_name
    
    tool_call = f"Use the tool `{tool_name}`"
    new_msg = (current_msg + " " + tool_call).strip() if current_msg else tool_call
    return new_msg, tool_name


def create_tools_panel(initial_choices=None, initial_value=None):
    choices = initial_choices or get_tool_names()
    value = initial_value or (choices[0] if choices else None)

    with gr.Accordion("🛠️ Available Tools", open=False, elem_classes=["panel"]):
        tool_dropdown = gr.Dropdown(
            label="Select Tool",
            choices=choices,
            value=value,
            interactive=True,
            elem_classes=["tool-dropdown"]
        )

        tool_info = gr.Textbox(
            label="Tool Description",
            interactive=False,
            lines=3,
            elem_classes=["tool-info"]
        )

        with gr.Row():
            refresh_btn = gr.Button("🔄 Refresh Tools", size="sm")
            insert_tool_btn = gr.Button("➕ Insert Tool", size="sm", variant="secondary")

    def refresh_tools():
        new_choices = get_tool_names()
        new_value = new_choices[0] if new_choices else None
        return gr.update(choices=new_choices, value=new_value)

    refresh_btn.click(
        fn=refresh_tools,
        outputs=[tool_dropdown]
    )

    return tool_dropdown, tool_info, refresh_btn, insert_tool_btn