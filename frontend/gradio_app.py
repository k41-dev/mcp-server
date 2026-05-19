#!/usr/bin/env python3
"""
gradio_app.py - Full MCP Agent Web UI (Gradio 5/6 Compatible)
Proper tool calling for BOTH Grok and Ollama
"""

import os
import json
import requests
from pathlib import Path
import gradio as gr
from openai import OpenAI
import ollama
from dotenv import load_dotenv

load_dotenv()


# ====================== CONFIG ======================
XAI_API_KEY = os.getenv("XAI_API_KEY")
XAI_MODEL = os.getenv("XAI_MODEL")
OLLAMA_URL = os.getenv("OLLAMA_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
MCP_URL = os.getenv("MCP_PUBLIC_URL")

openai_client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1") if XAI_API_KEY else None


# ====================== MCP FUNCTIONS ======================
def mcp_jsonrpc(method: str, params: dict = None):
    url = f"{MCP_URL.rstrip('/')}/mcp"
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            err = data["error"]
            if isinstance(err, dict):
                return {"error": err.get("message", str(err))}
            return {"error": str(err)}

        return data.get("result")

    except requests.exceptions.ConnectionError:
        return {"error": "❌ MCP Server nicht erreichbar (Verbindung abgelehnt)"}
    except requests.exceptions.Timeout:
        return {"error": "⏱️ MCP Server Timeout (Antwort zu langsam)"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"❌ HTTP Fehler {e.response.status_code}"}
    except Exception as e:
        return {"error": f"❌ Unerwarteter Fehler: {str(e)}"}


def get_mcp_tools():
    result = mcp_jsonrpc("tools/list")
    if result and "tools" in result:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("inputSchema", {})
                }
            }
            for tool in result["tools"]
        ]
    return []


def get_full_tools():
    """Returns the complete tool list from MCP including category (UI only)."""
    result = mcp_jsonrpc("tools/list")
    if result and "tools" in result:
        return result["tools"]
    return []


def call_mcp_tool(tool_name: str, arguments: dict = None):
    result = mcp_jsonrpc("tools/call", {"name": tool_name, "arguments": arguments or {}})
    
    if isinstance(result, dict) and "error" in result:
        return f"Error: {result['error']}"
    
    if result and "content" in result:
        texts = [item.get("text", "") for item in result["content"] if item.get("type") == "text"]
        return "\n".join(texts)
    
    return "No result returned"


# ====================== HISTORY SANITIZER ======================
def _sanitize_history(history: list) -> list:
    """Convert any corrupted list content back to clean string."""
    cleaned = []
    for h in history:
        content = h.get("content", "")
        if isinstance(content, list):
            if content and isinstance(content[0], dict) and "text" in content[0]:
                content = "\n".join(str(item.get("text", item)) for item in content)
            else:
                content = str(content)
        cleaned.append({
            "role": h.get("role", "user"),
            "content": str(content)
        })
    return cleaned


# ====================== CHAT LOGIC ======================
def chat_with_agent(message: str, history: list, model_choice: str):
    tools = get_mcp_tools()
    clean_history = _sanitize_history(history)

    # === Dynamic Model Name ===
    if model_choice == "Grok":
        model_display = XAI_MODEL
        is_grok = True
    else:
        model_display = OLLAMA_MODEL
        is_grok = False
    
    # === Dynamic Prompt + Versioning ===
    prompt_data = mcp_jsonrpc("prompts/get_dynamic", {"model": "grok" if is_grok else "ollama"})
    system_prompt = prompt_data.get("prompt", "") if prompt_data else ""
    current_version = prompt_data.get("version", "v1") if prompt_data else "v1"

    if not hasattr(chat_with_agent, "_last_prompt_version"):
        chat_with_agent._last_prompt_version = None

    include_system = (
        len(clean_history) == 0 or 
        current_version != chat_with_agent._last_prompt_version
    )

    if include_system:
        messages = [{"role": "system", "content": system_prompt}] + clean_history + [{"role": "user", "content": message}]
        chat_with_agent._last_prompt_version = current_version
    else:
        messages = clean_history + [{"role": "user", "content": message}]

    # === Get active Persona + Skill ===
    active_persona_name = "None"
    active_skill_name = "None"

    try:
        persona_result = call_mcp_tool("get_active_persona", {})
        if isinstance(persona_result, str) and "name" in persona_result:
            p = json.loads(persona_result)
            active_persona_name = p.get("name", "None")
    except:
        pass

    try:
        skill_result = call_mcp_tool("get_active_skill", {})
        if isinstance(skill_result, str) and "name" in skill_result:
            s = json.loads(skill_result)
            active_skill_name = s.get("name", "None")
    except:
        pass

    context_parts = []
    if active_persona_name and active_persona_name != "None":
        context_parts.append(f"🎭 {active_persona_name}")
    if active_skill_name and active_skill_name != "None":
        context_parts.append(f"🛠️ {active_skill_name}")

    context_line = " • ".join(context_parts) if context_parts else ""

    # ========== GROK PATH ==========
    if is_grok:
        if not openai_client:
            return history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": "❌ XAI_API_KEY is not configured"}
            ]

        tool_steps = [] 

        grok_messages = [{"role": "system", "content": system_prompt}] + clean_history + [{"role": "user", "content": message}]

        for _ in range(6):
            try:
                response = openai_client.chat.completions.create(
                    model=XAI_MODEL,
                    messages=grok_messages,
                    tools=tools if tools else None,
                    tool_choice="auto",
                    temperature=0.7,
                )
                msg = response.choices[0].message

                if msg.tool_calls:
                    grok_messages.append(msg.model_dump(exclude_none=True))
                    for tc in msg.tool_calls:
                        tool_name = tc.function.name
                        args = json.loads(tc.function.arguments or "{}")
                        result = call_mcp_tool(tool_name, args)
                        tool_steps.append(f"🔧 `{tool_name}`")

                        grok_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result
                        })
                    continue

                # === Final Answer + Tool Summary ===
                content = msg.content or "(No response)"
                final_msg = f"**{model_display}**"
                
                if context_line:
                    final_msg += f"\n*{context_line}*"
                final_msg += f"\n\n{content}"

                if tool_steps:
                    final_msg += "\n\n" + "\n".join(tool_steps)

                assistant_text = content or ""
                if assistant_text:
                    call_mcp_tool("add_chat_turn", {"role": "assistant", "content": assistant_text})

                return history + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": final_msg}
                ]

            except Exception as e:
                return history + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": f"Error: {str(e)}"}
                ]

        return history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": "Max tool turns reached."}
        ]

    # ========== OLLAMA PATH ==========
    else:
        try:
            ollama_client = ollama.Client(host=OLLAMA_URL)

            messages = [{"role": "system", "content": system_prompt}] + clean_history + [{"role": "user", "content": message}]

            MAX_TURNS = 4
            tool_steps = []

            for _ in range(MAX_TURNS):
                resp = ollama_client.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                tools=tools if tools else None,
                )

                message_obj = resp.get("message", {})
                content = message_obj.get("content", "") or ""
                tool_calls = message_obj.get("tool_calls", []) or []

                # === Verbesserter raw-JSON Fallback ===
                if not tool_calls and isinstance(content, str) and content.strip().startswith("{"):
                    try:
                        parsed = json.loads(content.strip())
                        if isinstance(parsed, dict) and parsed.get("name"):
                            tool_name = parsed.get("name")
                            # Nur bekannte Tools akzeptieren
                            if any(t["function"]["name"] == tool_name for t in tools):
                                args = parsed.get("parameters") or parsed.get("arguments") or {}
                                if isinstance(args, str):
                                    try:
                                        args = json.loads(args)
                                    except:
                                        args = {}
                                tool_calls = [{
                                    "function": {
                                        "name": tool_name,
                                        "arguments": args
                                    }
                                }]
                                content = ""
                    except Exception as e:
                        print(f"[Ollama Fallback] JSON parse failed: {e}")

                if tool_calls:
                    messages.append({
                        "role": "assistant",
                        "content": content,
                        "tool_calls": tool_calls
                    })

                    for tc in tool_calls:
                        func = tc.get("function", {})
                        tool_name = func.get("name")
                        args = func.get("arguments", {})

                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except:
                                args = {}

                        if tool_name:
                            # Zusätzliche Validierung
                            if any(t["function"]["name"] == tool_name for t in tools):
                                result = call_mcp_tool(tool_name, args)
                                tool_steps.append(f"🔧 `{tool_name}`")
                                messages.append({"role": "tool", "content": result})
                            else:
                                print(f"[Ollama] Ignored unknown tool: {tool_name}")

                    continue

                # === Final Answer ===
                final_msg = f"**{model_display}**"
                if context_line:
                    final_msg += f"\n*{context_line}*"
                final_msg += f"\n\n{content or ''}"

                if tool_steps:
                    final_msg += "\n\n" + "\n".join(tool_steps)

                if content:
                    call_mcp_tool("add_chat_turn", {"role": "assistant", "content": content})

                return history + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": final_msg}
                ]

        except Exception as e:
            return history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": f"Ollama error: {str(e)}"}
            ]


# ====================== UI ACTIONS ======================
def get_status():
    """Liefert 4 separate Status-Werte für die neuen Boxen."""
    try:
        tools = get_mcp_tools()
        tool_count = len(tools) if tools else 0

        # Aktiven Kontext holen
        persona_result = call_mcp_tool("get_active_persona", {})
        skill_result = call_mcp_tool("get_active_skill", {})

        persona_name = "None"
        skill_name = "None"

        if isinstance(persona_result, str) and "name" in persona_result:
            try:
                p = json.loads(persona_result)
                persona_name = p.get("name", "None")
            except:
                pass

        if isinstance(skill_result, str) and "name" in skill_result:
            try:
                s = json.loads(skill_result)
                skill_name = s.get("name", "None")
            except:
                pass

        prompt_data = mcp_jsonrpc("prompts/get_dynamic", {"model": "grok"})
        version = prompt_data.get("version", "unknown") if prompt_data else "unknown"

        conn = f"✅ Connected • {tool_count} tools"
        prompt = f"📜 Prompt: {version}"
        persona = f"🎭 Persona: {persona_name}"
        skill = f"🛠️ Skill: {skill_name}"

        return conn, prompt, persona, skill

    except Exception as e:
        return f"❌ Error: {str(e)}", "📜 Prompt: error", "🎭 Persona: error", "🛠️ Skill: error"


def refresh_all(model_choice_value: str):
    """Zentrale Refresh-Funktion – aktualisiert Status, Tools und Prompt gleichzeitig."""
    conn, prompt, persona, skill = get_status()
    return conn, prompt, persona, skill


def get_memories():
    return call_mcp_tool("list_memories", {})


def clear_memory():
    return call_mcp_tool("clear_memory", {})


def get_chat_history():
    return call_mcp_tool("list_chat_history", {"limit": 20})


def clear_chat_history():
    return call_mcp_tool("clear_chat_history", {})


# ====================== PERSONA CONTROL ======================
def get_persona_choices():
    """Returns a clean list of personas for the dropdown.
    Unterstützt jetzt das neue strukturierte JSON-Format von list_personas.
    """
    try:
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

    result = call_mcp_tool("set_active_persona", {
        "persona_name": persona_name,
        "intensity": int(intensity)
    })

    if isinstance(result, str) and ("Error" in result or "error" in result.lower()):
        return f"❌ Fehler beim Aktivieren von '{persona_name}': {result}"

    return f"✅ {persona_name}"


def reset_persona():
    """Clear the active persona on the backend."""
    call_mcp_tool("clear_active_persona", {})
    return "Default"


def load_initial_personas():
    choices = get_persona_choices()
    
    normalized = [c.lower() for c in choices]
    
    if "default" not in normalized:
        choices = ["Default"] + choices
    else:
        # "Default" an erste Stelle setzen + Duplikate entfernen
        choices = ["Default"] + [c for c in choices if c.lower() != "default"]
    
    return gr.update(choices=choices, value="Default")


# ====================== SKILL CONTROL ======================
def get_skill_choices():
    """Robuster Parser für list_skills (extrahiert JSON auch bei zusätzlichem Text)."""
    try:
        result = call_mcp_tool("list_skills", {})
        
        if not isinstance(result, str):
            return []

        # JSON-Teil extrahieren (vom ersten [ bis zum letzten ])
        start = result.find("[")
        end = result.rfind("]") + 1

        if start == -1 or end == 0:
            print("[get_skill_choices] Kein JSON-Array gefunden")
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
    """Aktiviert einen Skill über das neue execute_skill Tool."""
    if not skill_name or skill_name == "None":
        return "Please select a skill first."

    result = call_mcp_tool("execute_skill", {
        "skill_name": skill_name
    })

    if isinstance(result, str) and ("Error" in result or "error" in result.lower()):
        return f"❌ Fehler beim Aktivieren von '{skill_name}': {result}"

    return f"✅ Skill aktiviert: {skill_name}"


def reset_skill():
    """Clear the active skill on the backend."""
    call_mcp_tool("clear_active_skill", {})
    return "None"


def load_initial_skills():
    choices = get_skill_choices()
    
    if "None" not in [c.lower() for c in choices]:
        choices = ["None"] + choices
    else:
        choices = ["None"] + [c for c in choices if c.lower() != "none"]
    
    return gr.update(choices=choices, value="None")


def get_active_context_boxes():
    """Liefert die aktuell aktiven Persona- und Skill-Namen für die oberen Anzeige-Boxen."""
    try:
        persona_result = call_mcp_tool("get_active_persona", {})
        skill_result = call_mcp_tool("get_active_skill", {})

        persona_name = "Default"
        if isinstance(persona_result, str) and "name" in persona_result:
            try:
                p = json.loads(persona_result)
                if p.get("name"):
                    persona_name = p["name"].title()
            except:
                pass

        skill_name = "None"
        if isinstance(skill_result, str) and "name" in skill_result:
            try:
                s = json.loads(skill_result)
                if s.get("name"):
                    skill_name = s["name"].title()
            except:
                pass

        return persona_name, skill_name
    except Exception:
        return "Default", "None"


def get_system_prompt(model_choice: str):
    """Fetch the current dynamic system prompt + version (with debug)."""
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


def get_tool_names():
    """Returns nicely formatted choices with category prefix. Very stable."""
    try:
        tools = get_full_tools()
        
        if not tools:
            print("[DEBUG] get_tool_names: No tools received from MCP")
            return gr.update(choices=[], value=None)

        # Sort by category, then name
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
    """Zeigt die reine Tool-Beschreibung."""
    if not selected_value:
        return ""

    if isinstance(selected_value, list):
        if not selected_value:
            return ""
        selected = str(selected_value[0]).strip()
    else:
        selected = str(selected_value).strip()

    tools = get_full_tools()

    import re
    match = re.search(r'\[.*?\]\s*(.+)', selected)
    tool_name = match.group(1).strip() if match else selected

    for t in tools:
        if t.get("name") == tool_name or t.get("name") == selected:
            return t.get("description", "No description available.")

    return "Kein Tool gefunden."


def insert_tool(selected_value, current_message):
    """
    Fügt den echten Tool-Namen (ohne Kategorie-Prefix) in das Message-Feld ein
    und setzt das Dropdown zurück, damit dasselbe Tool sofort wieder ausgewählt werden kann.
    """
    if not selected_value:
        return current_message or "", "", gr.update(value=None)

    if isinstance(selected_value, list):
        if not selected_value:
            return current_message or "", "", gr.update(value=None)
        selected = str(selected_value[0]).strip()
    else:
        selected = str(selected_value).strip()

    # Extrahiere echten Namen (funktioniert bei "[core] calculate" oder "calculate")
    import re
    match = re.search(r'\[.*?\]\s*(.+)', selected)
    tool_name = match.group(1).strip() if match else selected

    if current_message and str(current_message).strip():
        new_message = f"{str(current_message).strip()} {tool_name}"
    else:
        new_message = tool_name

    # Tool-Beschreibung für die Info-Box zurückgeben
    tools = get_full_tools()
    description = "No description found for this tool."
    for t in tools:
        if t.get("name") == tool_name:
            description = t.get("description", "No description available.")
            break

    return new_message, description, gr.update()


# ====================== MAIN UI ======================
def create_ui():
    css_path = Path(__file__).parent / "style.css"
    custom_css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""

    with gr.Blocks(title="MCP-Server", css=custom_css) as demo:
        gr.Markdown("# 🚀 MCP-Server")

        # ========== TOP STATUS BAR ==========
        with gr.Row(elem_classes=["panel", "status-bar"]):
            with gr.Row(scale=5):
                conn_status = gr.Textbox(
                    value="✅ Connected • 32 tools",
                    label="Connection",
                    interactive=False,
                    scale=3
                )
                prompt_version = gr.Textbox(
                    value="📜 Prompt: a2fc2d1d8f",
                    label="Prompt Version",
                    interactive=False,
                    scale=2
                )
                active_persona = gr.Textbox(
                    value="🎭 Persona: None",
                    label="Persona",
                    interactive=False,
                    scale=2
                )
                active_skill = gr.Textbox(
                    value="🛠️ Skill: None",
                    label="Skill",
                    interactive=False,
                    scale=2
                )

            model_choice = gr.Radio(
                ["Grok", "Ollama"],
                value="Grok",
                label="Model",
                scale=1
            )
            refresh_all_btn = gr.Button("🔄 Refresh All", size="sm", scale=1)

        # ========== TWO COLUMN LAYOUT ==========
        with gr.Row(elem_classes=["main-layout"]):
            
            # LEFT: Chat
            with gr.Column(scale=3, elem_classes=["chat-column"]):
                
                chatbot = gr.Chatbot(
                    label="Agent Conversation",
                    height=800,
                    show_label=True,
                    avatar_images=(
                        None,
                        "https://api.dicebear.com/7.x/bottts/svg?seed=grok"
                    ),
                    elem_classes=["panel", "chat-panel"]
                )
            
                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="Type your message here...",
                        scale=8,
                        container=False
                    )
                    send_btn = gr.Button(
                    "Send",
                        variant="primary",                        scale=1
                    )  

            # RIGHT: Menue
            with gr.Column(scale=1, elem_classes=["menue-column"]):

                # === System Prompt Viewer ===
                with gr.Accordion("📜 System Prompt", open=False, elem_classes=["panel"]):
                    with gr.Row():
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
                    # CSS für feste maximale Höhe + Scrollbar
                    gr.HTML("""
                    <style>
                    .system-prompt-box {
                        max-height: none !important; 
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

                    # === Active Context Summary (immer sichtbar) ===
                    with gr.Row():
                        active_persona_display = gr.Textbox(
                            label="🎭 Active Persona",
                            value="Default",
                            interactive=False,
                            scale=1
                        )
                        active_skill_display = gr.Textbox(
                            label="🛠️ Active Skill",
                            value="None",
                            interactive=False,
                            scale=1
                        )

                    # === Persona Control ===
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

                        # Wiring
                        apply_btn.click(
                            apply_persona,
                            inputs=[persona_dropdown, intensity_slider]
                        ).then(
                            get_system_prompt,
                            inputs=[model_choice],
                            outputs=system_prompt_box
                        ).then(
                            get_status,
                            outputs=[conn_status, prompt_version, active_persona, active_skill]
                        ).then(
                            get_active_context_boxes, 
                            outputs=[active_persona_display, active_skill_display]
                        )

                        reset_btn.click(
                            reset_persona
                        ).then(
                            get_system_prompt,
                            inputs=[model_choice],
                            outputs=system_prompt_box
                        ).then(
                            get_status,
                            outputs=[conn_status, prompt_version, active_persona, active_skill]
                        ).then(
                            get_active_context_boxes, 
                            outputs=[active_persona_display, active_skill_display]
                        ).then(
                            lambda: "Default",
                            outputs=persona_dropdown
                        )

                        load_btn.click(
                            load_initial_personas, 
                            outputs=persona_dropdown
                        )

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

                        # Wiring
                        apply_skill_btn.click(
                            apply_skill,
                            inputs=[skill_dropdown]
                        ).then(
                            get_system_prompt,
                            inputs=[model_choice],
                            outputs=system_prompt_box
                        ).then(
                            get_status,
                            outputs=[conn_status, prompt_version, active_persona, active_skill]
                        ).then(
                            get_active_context_boxes, 
                            outputs=[active_persona_display, active_skill_display]
                        )

                        reset_skill_btn.click(
                            reset_skill          
                        ).then(
                            get_system_prompt,
                            inputs=[model_choice],
                            outputs=system_prompt_box
                        ).then(
                            get_status,
                            outputs=[conn_status, prompt_version, active_persona, active_skill]
                        ).then(
                            get_active_context_boxes, 
                            outputs=[active_persona_display, active_skill_display]
                        ).then(
                            lambda: "None",
                            outputs=skill_dropdown
                        )

                        load_skills_btn.click(
                            load_initial_skills, 
                            outputs=skill_dropdown
                        )

                # ====================== AVAILABLE TOOLS ======================
                with gr.Accordion("🛠️ Available Tools", open=True, elem_classes=["panel"]) as tools_accordion:

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

                    # When accordion is expanded → auto-refresh tools (more reliable than only demo.load)
                    tools_accordion.expand(
                        fn=get_tool_names,
                        outputs=tool_dropdown
                    )

                    # Dropdown selection → insert + show description
                    tool_dropdown.change(
                        fn=update_tool_info,
                        inputs=[tool_dropdown],
                        outputs=[tool_info]
                    )

                    refresh_btn.click(
                        fn=get_tool_names,
                        outputs=[tool_dropdown]
                    ).then(
                        fn=lambda x: update_tool_info(x) if x else "",
                        inputs=[tool_dropdown],
                        outputs=[tool_info]
                    )

                    insert_tool_btn.click(
                        fn=insert_tool,
                        inputs=[tool_dropdown, msg],
                        outputs=[msg, tool_info, tool_dropdown]
                    )

                # === Memory Viewer ===
                with gr.Accordion("🧠 Memory", open=True, elem_classes=["panel"]):
                    memory_box = gr.Textbox(
                        lines=12,
                        interactive=False,
                        label="Memory Output",
                        show_label=False,
                        elem_id="memory_box",
                        elem_classes=["panel"]
                    )

                    # Long-term Memory
                    gr.Markdown("**Long-term Memory**")
                    with gr.Row():
                        gr.Button("Show LT-Memory", size="sm").click(get_memories, outputs=memory_box)
                        gr.Button("Clear LT-Memory", size="sm", variant="stop").click(clear_memory, outputs=memory_box)

                    # Chat History
                    gr.Markdown("**Chat History**")
                    with gr.Row():
                        gr.Button("Show Chat-Memory", size="sm").click(get_chat_history, outputs=memory_box)
                        gr.Button("Clear Chat-Memory", size="sm", variant="stop").click(clear_chat_history, outputs=memory_box)

                    # Danger Zone
                    gr.Markdown("**Danger Zone**")
                    gr.Button("🗑️ Full Reset (Nuclear)", size="lg", variant="stop").click(
                        lambda: call_mcp_tool("full_reset", {}), 
                        outputs=memory_box
                    )
                   
        # Chat logic
        def respond(user_message, chat_history, model):
            if not user_message.strip():
                return chat_history, ""

            call_mcp_tool("add_chat_turn", {"role": "user", "content": user_message})

            new_history = chat_with_agent(user_message, chat_history, model)
            return new_history, ""

        send_btn.click(respond, [msg, chatbot, model_choice], [chatbot, msg])
        msg.submit(respond, [msg, chatbot, model_choice], [chatbot, msg])

        demo.load(get_status, outputs=[conn_status, prompt_version, active_persona, active_skill])
        demo.load(get_system_prompt, inputs=[model_choice], outputs=system_prompt_box)
        demo.load(load_initial_personas, outputs=persona_dropdown)
        demo.load(load_initial_skills, outputs=skill_dropdown)
        demo.load(get_tool_names, outputs=tool_dropdown)
        demo.load(get_active_context_boxes, outputs=[active_persona_display, active_skill_display])
        
        model_choice.change(get_system_prompt, inputs=[model_choice], outputs=system_prompt_box)

        # ========== ZENTRALE REFRESH FUNKTION ==========
        refresh_all_btn.click(
            fn=refresh_all,
            inputs=[model_choice],
            outputs=[conn_status, prompt_version, active_persona, active_skill]
        )

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )