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


# === Modular UI Components ===
from components import create_status_bar
from components.prompt_viewer import create_prompt_viewer, get_system_prompt
from components.persona_control import create_persona_control, apply_persona, reset_persona, load_initial_personas
from components.skill_control import create_skill_control, apply_skill, reset_skill, load_initial_skills
from components.tools_panel import create_tools_panel, get_tool_names, update_tool_info, insert_tool
from components.memory_panel import create_memory_panel, get_memories, clear_memory, get_chat_history, clear_chat_history, full_reset


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


# ====================== MAIN UI ======================
def create_ui():
    css_path = Path(__file__).parent / "style.css"
    custom_css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""

    with gr.Blocks(title="MCP-Server", css=custom_css) as demo:
        gr.Markdown("# 🚀 MCP-Server")

        # ========== TOP STATUS BAR ==========
        conn_status, prompt_version, active_persona, active_skill, model_choice = create_status_bar()

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
                    send_btn = gr.Button("Send", variant="primary", scale=1)

            # RIGHT: Menue
            with gr.Column(scale=1, elem_classes=["menue-column"]):

                # === System Prompt Viewer ===
                system_prompt_box = create_prompt_viewer()

                # === Persona Control ===
                persona_dropdown, intensity_slider, apply_btn, reset_btn, load_btn = create_persona_control()

                # === Persona Event Wiring ===
                apply_btn.click(
                    apply_persona,
                    inputs=[persona_dropdown, intensity_slider]
                ).then(
                    get_system_prompt,
                    inputs=[model_choice],
                    outputs=[system_prompt_box]
                ).then(
                    get_status,
                    outputs=[conn_status, prompt_version, active_persona, active_skill]
                )

                reset_btn.click(
                    reset_persona
                ).then(
                    get_system_prompt,
                    inputs=[model_choice],
                    outputs=[system_prompt_box]
                ).then(
                    get_status,
                    outputs=[conn_status, prompt_version, active_persona, active_skill]
                ).then(
                    lambda: "Default",
                    outputs=[persona_dropdown]
                )

                load_btn.click(
                    load_initial_personas,
                    outputs=[persona_dropdown]
                )

                # === Skill Control ===
                skill_dropdown, apply_skill_btn, reset_skill_btn, load_skills_btn = create_skill_control()

                # === Skill Event Wiring ===
                apply_skill_btn.click(
                    apply_skill,
                    inputs=[skill_dropdown]
                ).then(
                    get_system_prompt,
                    inputs=[model_choice],
                    outputs=[system_prompt_box]
                ).then(
                    get_status,
                    outputs=[conn_status, prompt_version, active_persona, active_skill]
                )

                reset_skill_btn.click(
                    reset_skill
                ).then(
                    get_system_prompt,
                    inputs=[model_choice],
                    outputs=[system_prompt_box]
                ).then(
                    get_status,
                    outputs=[conn_status, prompt_version, active_persona, active_skill]
                ).then(
                    lambda: "None",
                    outputs=[skill_dropdown]
                )

                load_skills_btn.click(
                    load_initial_skills,
                    outputs=[skill_dropdown]
                )

                # === Tools Panel ===
                tool_dropdown, tool_info, refresh_btn, insert_tool_btn = create_tools_panel()

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

                # === Memory Panel ===
                memory_box, show_lt_btn, clear_lt_btn, show_chat_btn, clear_chat_btn, full_reset_btn = create_memory_panel()

                show_lt_btn.click(get_memories, outputs=[memory_box])
                clear_lt_btn.click(clear_memory, outputs=[memory_box])

                show_chat_btn.click(get_chat_history, outputs=[memory_box])
                clear_chat_btn.click(clear_chat_history, outputs=[memory_box])

                full_reset_btn.click(full_reset, outputs=[memory_box])

        # ====================== CHAT LOGIC ======================
        def respond(user_message, chat_history, model):
            if not user_message.strip():
                return chat_history, ""

            call_mcp_tool("add_chat_turn", {"role": "user", "content": user_message})
            new_history = chat_with_agent(user_message, chat_history, model)
            return new_history, ""

        send_btn.click(
            respond, 
            [msg, chatbot, model_choice], 
            [chatbot, msg]
        ).then(
            get_status,
            outputs=[conn_status, prompt_version, active_persona, active_skill]
        )

        msg.submit(
            respond, 
            [msg, chatbot, model_choice], 
            [chatbot, msg]
        ).then(
            get_status,
            outputs=[conn_status, prompt_version, active_persona, active_skill]
        )

        # ====================== DEMO LOAD ======================
        demo.load(get_status, outputs=[conn_status, prompt_version, active_persona, active_skill])
        demo.load(get_system_prompt, inputs=[model_choice], outputs=[system_prompt_box])
        demo.load(load_initial_personas, outputs=[persona_dropdown])
        demo.load(load_initial_skills, outputs=[skill_dropdown])
        demo.load(get_tool_names, outputs=[tool_dropdown])
        
        model_choice.change(get_system_prompt, inputs=[model_choice], outputs=[system_prompt_box])

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )