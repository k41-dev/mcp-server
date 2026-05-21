#!/usr/bin/env python3
"""
chat_handler.py - Zentrale Chat-Logik für das Frontend (als Komponente)
"""

import os
import json
from .mcp_client import mcp_jsonrpc, call_mcp_tool, get_mcp_tools


XAI_API_KEY = os.getenv("XAI_API_KEY")
XAI_MODEL = os.getenv("XAI_MODEL")
OLLAMA_URL = os.getenv("OLLAMA_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")


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
    provider_name = "grok" if is_grok else "ollama"
    model_display = XAI_MODEL if is_grok else OLLAMA_MODEL

    # System Prompt + Versionierung (bleibt über MCP)
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

    # === Active Persona + Skill (Context Line) ===
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

    # ========== EINHEITLICHER MCP-PFAD ==========
    MAX_TURNS = 6 if is_grok else 4
    tool_steps = []

    for _ in range(MAX_TURNS):
        try:
            result = mcp_jsonrpc("models/chat", {
                "provider": provider_name,
                "messages": messages,
                "tools": tools if tools else None,
                "temperature": 0.7
            })

            if result and isinstance(result, dict) and "error" in result:
                return history + [{"role": "user", "content": message}, {"role": "assistant", "content": f"❌ MCP Error: {result['error']}"}]

            content = result.get("content", "") or ""
            tool_calls = result.get("tool_calls", []) or []

            if tool_calls:
                # Tool-Calls vorhanden → Messages erweitern und Tools ausführen
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
                        tool_steps.append(f"🔧 `{tool_name}`")
                        tool_result = call_mcp_tool(tool_name, args)
                        messages.append({
                            "role": "tool",
                            "content": tool_result,
                            "tool_call_id": tc.get("id", "")
                        })
                continue

            # === Keine Tool-Calls → Finale Antwort ===
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
            return history + [{"role": "user", "content": message}, {"role": "assistant", "content": f"Error: {str(e)}"}]

    return history + [{"role": "user", "content": message}, {"role": "assistant", "content": "Max tool turns reached."}]


# ====================== STATUS & REFRESH ======================
def get_status(model_choice_value: str = "Grok"):
    """Liefert den aktuellen Status für die Top-Status-Bar zurück."""
    try:
        # Tools zählen
        try:
            tools = get_mcp_tools()
            tool_count = len(tools) if tools else 0
        except Exception:
            tool_count = 0

        model_for_prompt = "grok" if model_choice_value == "Grok" else "ollama"

        # Active Persona & Skill holen
        persona_name = "None"
        skill_name = "None"

        try:
            persona_result = call_mcp_tool("get_active_persona", {})
            if isinstance(persona_result, str) and "name" in persona_result:
                persona_name = json.loads(persona_result).get("name", "None")
        except Exception:
            persona_name = "Error"

        try:
            skill_result = call_mcp_tool("get_active_skill", {})
            if isinstance(skill_result, str) and "name" in skill_result:
                skill_name = json.loads(skill_result).get("name", "None")
        except Exception:
            skill_name = "Error"

        # Aktuelle Prompt-Version holen
        try:
            prompt_data = mcp_jsonrpc("prompts/get_dynamic", {"model": model_for_prompt})
            version = prompt_data.get("version", "unknown") if prompt_data else "unknown"
        except Exception:
            version = "error"

        return (
            f"✅ Connected • {tool_count} tools",
            f"📜 Prompt: {version}",
            f"🎭 Persona: {persona_name}",
            f"🛠️ Skill: {skill_name}"
        )

    except Exception as e:
        # Fallback bei komplettem Fehler
        return (
            f"❌ Error: {str(e)}",
            "📜 Prompt: error",
            "🎭 Persona: error",
            "🛠️ Skill: error"
        )


def refresh_all(model_choice_value: str):
    return get_status()


def respond(user_message, chat_history, model):
    if not user_message.strip():
        return chat_history, ""
    call_mcp_tool("add_chat_turn", {"role": "user", "content": user_message})
    new_history = chat_with_agent(user_message, chat_history, model)
    return new_history, ""