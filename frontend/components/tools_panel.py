#!/usr/bin/env python3
"""
tools_panel.py - Tools Panel Komponente (verbessert)
"""

import gradio as gr
from .mcp_client import call_mcp_tool, get_mcp_tools


def get_tool_names():
    """Returns a list of available tool names for the dropdown."""
    try:
        tools = get_mcp_tools()
        if tools:
            return [t["function"]["name"] for t in tools]
        return []
    except Exception as e:
        print(f"[get_tool_names] Fehler: {e}")
        return []


def update_tool_info(tool_name):
    """Returns description + tool name for the selected tool."""
    if isinstance(tool_name, list):
        tool_name = tool_name[0] if tool_name else ""
    
    if not tool_name or not isinstance(tool_name, str) or tool_name.strip() == "":
        return ""
    
    try:
        tools = get_mcp_tools()
        for t in tools:
            if t.get("function", {}).get("name") == tool_name:
                desc = t.get("function", {}).get("description", "No description available.")
                # Schönes Format mit Tool-Name
                return f"**{tool_name}**\n\n{desc}"
        
        return f"**{tool_name}**\n\nTool nicht gefunden."
        
    except Exception as e:
        print(f"[update_tool_info] Fehler: {e}")
        return f"Error: {str(e)}"


def insert_tool(tool_name, current_msg: str):
    """Inserts the selected tool into the message input field (handles list)."""
    if isinstance(tool_name, list):
        tool_name = tool_name[0] if tool_name else ""
    
    if not tool_name:
        return current_msg or "", "", tool_name
    
    tool_call = f"Use the tool `{tool_name}`"
    new_msg = (current_msg + " " + tool_call).strip() if current_msg else tool_call
    return new_msg, "", tool_name


def create_tools_panel():
    """Erzeugt die komplette Tools Panel Accordion."""
    with gr.Accordion("🛠️ Available Tools", open=False, elem_classes=["panel"]):
        tool_dropdown = gr.Dropdown(
            label="Select Tool",
            choices=get_tool_names(),
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

    return tool_dropdown, tool_info, refresh_btn, insert_tool_btn