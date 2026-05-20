#!/usr/bin/env python3
"""
prompt_viewer.py - System Prompt Viewer Komponente (nur der Prompt-Bereich)
"""

import gradio as gr


def get_system_prompt(model_choice: str) -> str:
    """Fetch the current dynamic system prompt + version."""
    from gradio_app import mcp_jsonrpc   # lokaler Import (vermeidet Zirkel)

    print(f"[DEBUG] get_system_prompt called with model: {model_choice}")

    model = "grok" if model_choice == "Grok" else "ollama"

    data = mcp_jsonrpc("prompts/get_dynamic", {"model": model})
    print(f"[DEBUG] Received from MCP: {data}")

    if data and isinstance(data, dict) and "prompt" in data:
        prompt_text = data["prompt"]
        version = data.get("version", "unknown")
        header = f"**Prompt Version:** `{version}`\n\n"
        return header + prompt_text

    return f"❌ Could not retrieve system prompt. Response was: {data}"


def create_prompt_viewer() -> gr.Code:
    """Erzeugt nur den reinen System Prompt Viewer (Code-Block + zugehöriges CSS)."""
    with gr.Accordion("📜 System Prompt", open=False, elem_classes=["panel"]):
        system_prompt_box = gr.Code(
            language="markdown",
            lines=30,
            interactive=False,
            label="Current Dynamic System Prompt",
            show_label=False,
            elem_classes=["system-prompt-box"],
            elem_id="system_prompt_code",
            wrap_lines=False
        )

    # Nur das CSS, das direkt zum Prompt Viewer gehört
    gr.HTML("""
    <style>
    .system-prompt-box {
        max-height: 520px !important;
        height: auto !important;
        overflow-y: auto !important;
        overflow-x: auto !important;
        border-radius: 8px;
    }
    .system-prompt-box pre {
        margin: 0 !important;
    }
    </style>
    """)

    return system_prompt_box