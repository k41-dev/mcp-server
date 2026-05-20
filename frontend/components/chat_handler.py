#!/usr/bin/env python3
"""
chat_handler.py - Zentrale Chat-Logik für das Frontend (als Komponente)
"""

import json
from openai import OpenAI
import ollama
from dotenv import load_dotenv
import os

from .mcp_client import mcp_jsonrpc, call_mcp_tool, get_mcp_tools

load_dotenv()

XAI_API_KEY = os.getenv("XAI_API_KEY")
XAI_MODEL = os.getenv("XAI_MODEL")
OLLAMA_URL = os.getenv("OLLAMA_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

openai_client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1") if XAI_API_KEY else None


# ====================== HISTORY ======================
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


# ====================== CORE CHAT LOGIC ======================
def chat_with_agent(message: str, history: list, model_choice: str):
    tools = get_mcp_tools()
    clean_history = _sanitize_history(history)

    is_grok = model_choice == "Grok"
    model_display = XAI_MODEL if is_grok else OLLAMA_MODEL

    prompt_data = mcp_jsonrpc("prompts/get_dynamic", {"model": "grok" if is_grok else "ollama"})
    system_prompt = prompt_data.get("prompt", "") if prompt_data else ""
    current_version = prompt_data.get("version", "v1") if prompt_data else "v1"

    if not hasattr(chat_with_agent, "_last_prompt_version"):
        chat_with_agent._last_prompt_version = None

    include_system = (len(clean_history) == 0 or current_version != chat_with_agent._last_prompt_version)
    if include_system:
        messages = [{"role": "system", "content": system_prompt}] + clean_history + [{"role": "user", "content": message}]
        chat_with_agent._last_prompt_version = current_version
    else:
        messages = clean_history + [{"role": "user", "content": message}]

    # Active Persona + Skill (für Context Line)
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
            return history + [{"role": "user", "content": message}, {"role": "assistant", "content": "❌ XAI_API_KEY fehlt"}]

        grok_messages = [{"role": "system", "content": system_prompt}] + clean_history + [{"role": "user", "content": message}]
        tool_steps = []

        for _ in range(6):
            try:
                response = openai_client.chat.completions.create(
                    model=XAI_MODEL, messages=grok_messages, tools=tools if tools else None, tool_choice="auto", temperature=0.7
                )
                msg = response.choices[0].message
                if msg.tool_calls:
                    grok_messages.append(msg.model_dump(exclude_none=True))
                    for tc in msg.tool_calls:
                        tool_name = tc.function.name
                        args = json.loads(tc.function.arguments or "{}")
                        result = call_mcp_tool(tool_name, args)
                        tool_steps.append(f"🔧 `{tool_name}`")
                        grok_messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
                    continue

                content = msg.content or "(No response)"
                final_msg = f"**{model_display}**"
                if context_line:
                    final_msg += f"\n*{context_line}*"
                final_msg += f"\n\n{content}"
                if tool_steps:
                    final_msg += "\n\n" + "\n".join(tool_steps)

                if content:
                    call_mcp_tool("add_chat_turn", {"role": "assistant", "content": content})

                return history + [{"role": "user", "content": message}, {"role": "assistant", "content": final_msg}]
            except Exception as e:
                return history + [{"role": "user", "content": message}, {"role": "assistant", "content": f"Error: {str(e)}"}]

        return history + [{"role": "user", "content": message}, {"role": "assistant", "content": "Max tool turns reached."}]

    # ========== OLLAMA PATH ==========
    else:
        try:
            ollama_client = ollama.Client(host=OLLAMA_URL)
            messages = [{"role": "system", "content": system_prompt}] + clean_history + [{"role": "user", "content": message}]
            MAX_TURNS = 4
            tool_steps = []

            for _ in range(MAX_TURNS):
                resp = ollama_client.chat(model=OLLAMA_MODEL, messages=messages, tools=tools if tools else None)
                message_obj = resp.get("message", {})
                content = message_obj.get("content", "") or ""
                tool_calls = message_obj.get("tool_calls", []) or []

                # Raw-JSON Fallback
                if not tool_calls and isinstance(content, str) and content.strip().startswith("{"):
                    try:
                        parsed = json.loads(content.strip())
                        if isinstance(parsed, dict) and parsed.get("name"):
                            if any(t["function"]["name"] == parsed["name"] for t in tools):
                                tool_calls = [{"function": {"name": parsed["name"], "arguments": parsed.get("parameters") or parsed.get("arguments") or {}}}]
                                content = ""
                    except:
                        pass

                if tool_calls:
                    messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
                    for tc in tool_calls:
                        func = tc.get("function", {})
                        tool_name = func.get("name")
                        args = func.get("arguments", {})
                        if isinstance(args, str):
                            try: args = json.loads(args)
                            except: args = {}
                        if tool_name and any(t["function"]["name"] == tool_name for t in tools):
                            result = call_mcp_tool(tool_name, args)
                            tool_steps.append(f"🔧 `{tool_name}`")
                            messages.append({"role": "tool", "content": result})
                    continue

                final_msg = f"**{model_display}**"
                if context_line:
                    final_msg += f"\n*{context_line}*"
                final_msg += f"\n\n{content or ''}"
                if tool_steps:
                    final_msg += "\n\n" + "\n".join(tool_steps)

                if content:
                    call_mcp_tool("add_chat_turn", {"role": "assistant", "content": content})

                return history + [{"role": "user", "content": message}, {"role": "assistant", "content": final_msg}]

        except Exception as e:
            return history + [{"role": "user", "content": message}, {"role": "assistant", "content": f"Ollama error: {str(e)}"}]


# ====================== STATUS & REFRESH ======================
def get_status():
    try:
        tools = get_mcp_tools()
        tool_count = len(tools) if tools else 0

        persona_result = call_mcp_tool("get_active_persona", {})
        skill_result = call_mcp_tool("get_active_skill", {})

        persona_name = "None"
        skill_name = "None"
        if isinstance(persona_result, str) and "name" in persona_result:
            try: persona_name = json.loads(persona_result).get("name", "None")
            except: pass
        if isinstance(skill_result, str) and "name" in skill_result:
            try: skill_name = json.loads(skill_result).get("name", "None")
            except: pass

        prompt_data = mcp_jsonrpc("prompts/get_dynamic", {"model": "grok"})
        version = prompt_data.get("version", "unknown") if prompt_data else "unknown"

        return (
            f"✅ Connected • {tool_count} tools",
            f"📜 Prompt: {version}",
            f"🎭 Persona: {persona_name}",
            f"🛠️ Skill: {skill_name}"
        )
    except Exception as e:
        return f"❌ Error: {str(e)}", "📜 Prompt: error", "🎭 Persona: error", "🛠️ Skill: error"


def refresh_all(model_choice_value: str):
    return get_status()


def respond(user_message, chat_history, model):
    if not user_message.strip():
        return chat_history, ""
    call_mcp_tool("add_chat_turn", {"role": "user", "content": user_message})
    new_history = chat_with_agent(user_message, chat_history, model)
    return new_history, ""