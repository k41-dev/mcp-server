#!/usr/bin/env python3
"""
tools_panel.py - Available Tools Panel Komponente
"""

import gradio as gr
import re


def get_full_tools():
    from gradio_app import mcp_jsonrpc
    result = mcp_jsonrpc("tools/list")
    if result and "tools" in result:
        return result["tools"]
    return []


def get_tool_names():
    try:
        tools = get_full_tools()
        if not tools:
            return gr.update(choices=[], value=None)

        sorted_tools = sorted(tools, key=lambda t: (t.get("category", "core"), t["name"]))

        choices = []
        for t in sorted_tools:
            cat = t.get("category", "core")
            name = t["name"]
            label = f"[{cat}] {name}"
            choices.append(label)

        default_value = choices[0] if choices else None
        return gr.update(choices=choices, value=default_value)

    except Exception as e:
        print(f"[ERROR] get_tool_names failed: {e}")
        return gr.update(choices=[], value=None)


def update_tool_info(selected_value):
    if not selected_value:
        return ""

    if isinstance(selected_value, list):
        if not selected_value:
            return ""
        selected = str(selected_value[0]).strip()
    else:
        selected = str(selected_value).strip()

    tools = get_full_tools()
    match = re.search(r'\[.*?\]\s*(.+)', selected)
    tool_name = match.group(1).strip() if match else selected

    for t in tools:
        if t.get("name") == tool_name or t.get("name") == selected:
            return t.get("description", "No description available.")

    return "Kein Tool gefunden."


def insert_tool(selected_value, current_message):
    if not selected_value:
        return current_message or "", "", gr.update(value=None)

    if isinstance(selected_value, list):
        if not selected_value:
            return current_message or "", "", gr.update(value=None)
        selected = str(selected_value[0]).strip()
    else:
        selected = str(selected_value).strip()

    match = re.search(r'\[.*?\]\s*(.+)', selected)
    tool_name = match.group(1).strip() if match else selected

    if current_message and str(current_message).strip():
        new_message = f"{str(current_message).strip()} {tool_name}"
    else:
        new_message = tool_name

    tools = get_full_tools()
    description = "No description found for this tool."
    for t in tools:
        if t.get("name") == tool_name:
            description = t.get("description", "No description available.")
            break

    return new_message, description, gr.update()


def create_tools_panel():
    with gr.Accordion("🛠️ Available Tools", open=True, elem_classes=["panel"]):
        tool_dropdown = gr.Dropdown(
            label="Select Tool",
            choices=[],
            interactive=True,
            allow_custom_value=False,
            multiselect=False
        )

        tool_info = gr.Textbox(
            label="Tool Description",
            interactive=False,
            lines=3
        )

        with gr.Row():
            refresh_btn = gr.Button("🔄 Refresh Tools", size="sm")
            insert_tool_btn = gr.Button("➕ Insert Tool", variant="secondary", size="sm")

    return tool_dropdown, tool_info, refresh_btn, insert_tool_btn