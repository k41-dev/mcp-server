#!/usr/bin/env python3
"""
chat_handler.py - Zentrale Chat-Logik für das Frontend (als Komponente)
"""

import os
import json
import httpx
from .mcp_client import mcp_jsonrpc, call_mcp_tool, get_mcp_tools
from .prompt_viewer import get_system_prompt


XAI_API_KEY = os.getenv("XAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# ====================== HELPER ======================
def _get_context_line() -> str:
    """Holt aktive Persona + Skill + aktuelle Session und baut die Context-Line."""
    active_persona_name = "None"
    active_skill_name = "None"
    current_session = "?"

    try:
        # Aktive Session
        session_result = call_mcp_tool("get_active_session", {})
        if isinstance(session_result, str):
            try:
                session_data = json.loads(session_result)
                current_session = session_data.get("session_id", "?")
            except:
                pass

        # Persona
        persona_result = call_mcp_tool("get_active_persona", {})
        if isinstance(persona_result, str):
            try:
                data = json.loads(persona_result)
                if isinstance(data, dict) and "name" in data:
                    active_persona_name = data.get("name", "None")
            except:
                pass

        # Skill
        skill_result = call_mcp_tool("get_active_skill", {})
        if isinstance(skill_result, str):
            try:
                data = json.loads(skill_result)
                if isinstance(data, dict) and "name" in data:
                    active_skill_name = data.get("name", "None")
            except:
                pass

        # === NEU: Aktives Model aus Backend lesen ===
        provider_result = call_mcp_tool("get_active_provider", {})
        if isinstance(provider_result, str):
            try:
                data = json.loads(provider_result)
                provider = data.get("active_provider", "xai")
                model_map = {
                    "xai": os.getenv("XAI_MODEL", "grok"),
                    "openai": os.getenv("OPENAI_MODEL", "gpt-4o"),
                    "anthropic": os.getenv("ANTHROPIC_MODEL", "claude"),
                    "ollama": os.getenv("OLLAMA_MODEL", "llama3"),
                }
                current_model = model_map.get(provider, "?")
            except:
                pass

    except Exception:
        pass

    parts = []
    if active_persona_name and active_persona_name != "None":
        parts.append(f"🎭 {active_persona_name}")
    if active_skill_name and active_skill_name != "None":
        parts.append(f"🛠️ {active_skill_name}")
    parts.append(f"📍 Session {current_session}")

    return " • ".join(parts) if parts else ""


def switch_model_provider(model_choice_value: str) -> str:
    mapping = {
        "xAI": "xai",
        "Ollama": "ollama",
        "OpenAI": "openai",
        "Anthropic": "anthropic",
    }
    provider = mapping.get(model_choice_value, "xai")
    result = call_mcp_tool("set_active_provider", {"provider": provider})
    return result


def _stream_final_answer(base_history: list, final_msg: str):
    import re
    import time

    chunks = re.split(r'(?<=[.!?])\s+|\n\s*\n', final_msg.strip())
    chunks = [c.strip() for c in chunks if c.strip()]

    streamed_content = ""

    for chunk in chunks:
        streamed_content += chunk + "\n\n"
        current_msg = streamed_content.strip()
        yield base_history + [{"role": "assistant", "content": current_msg}]
        time.sleep(0.12)

    yield base_history + [{"role": "assistant", "content": final_msg}]


def _build_tool_status_message(model_display: str, context_line: str, tool_names: list, step_count: int) -> str:
    if not tool_names:
        return f"**{model_display}**\n*{context_line}*\n\n🔧 Verarbeite Tools ..."

    tool_list = ", ".join([f"`{name}`" for name in tool_names])
    spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    frame = spinner_frames[step_count % len(spinner_frames)]

    return (
        f"**{model_display}**\n"
        f"*{context_line}*\n\n"
        f"{frame}  **Führe Tool(s) aus:** {tool_list}"
    )


# ====================== HELPER ======================
def _save_final_assistant_message(content: str, tool_steps: list, tool_calls: list, context_line: str = ""):
    """
    Speichert die finale Assistant-Antwort.
    Bei Tool-Nutzung werden die Tool-Namen sauber am Ende der Nachricht gespeichert,
    damit sie nach einem Session-Wechsel wiederhergestellt werden können.
    """
    from .mcp_client import call_mcp_tool

    final_content = (content or "").strip()

    if tool_steps or tool_calls:
        # Saubere Liste der verwendeten Tools extrahieren
        used_tools = set()
        for step in tool_steps:
            if "`" in step:
                tool_name = step.split("`")[1]
                used_tools.add(tool_name)
            else:
                clean = step.replace("🔧 ", "").strip()
                if clean:
                    used_tools.add(clean)

        if used_tools:
            tools_list = ",".join(sorted(used_tools))
            # Strukturierter Marker (wird später beim Laden erkannt)
            final_content += f"\n\n<!--TOOL_USAGE:{tools_list}-->"

    if final_content:
        call_mcp_tool("add_chat_turn", {"role": "assistant", "content": final_content})


def _prepare_messages(history: list, user_message: str, provider: str = "grok"):
    clean_history = _sanitize_history(history)

    # Dynamischen System-Prompt holen
    prompt_data = mcp_jsonrpc("prompts/get_dynamic", {"model": provider})
    system_prompt = prompt_data.get("prompt", "") if prompt_data else ""
    current_version = prompt_data.get("version", "v1") if prompt_data else "v1"

    func = _prepare_messages
    if not hasattr(func, "_last_prompt_version"):
        func._last_prompt_version = None

    include_system = (len(clean_history) == 0 or current_version != func._last_prompt_version)

    if include_system:
        messages = [{"role": "system", "content": system_prompt}] + clean_history + [{"role": "user", "content": user_message}]
        func._last_prompt_version = current_version
    else:
        messages = clean_history + [{"role": "user", "content": user_message}]

    return messages, current_version


# ====================== HISTORY ======================
def _sanitize_history(history: list) -> list:
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


# ====================== CORE AGENT ======================
def _chat_with_agent_generator(message: str, history: list, model_choice: str):
    tools = get_mcp_tools()

    context_line = _get_context_line()

    # Aktiven Skill sicher ermitteln (für Long-Running-Modus)
    active_skill_name = ""
    try:
        skill_result = call_mcp_tool("get_active_skill", {})
        if isinstance(skill_result, str):
            data = json.loads(skill_result)
            if isinstance(data, dict):
                active_skill_name = data.get("name", "").lower().strip()
    except Exception:
        active_skill_name = ""

    if model_choice == "xAI":
        provider_name = "xai"
        model_display = os.getenv("XAI_MODEL")
        MAX_TURNS = 10 if active_skill_name == "long_running_autonomous" else 6

    elif model_choice == "OpenAI":
        provider_name = "openai"
        model_display = os.getenv("OPENAI_MODEL")
        MAX_TURNS = 10 if active_skill_name == "long_running_autonomous" else 6

    elif model_choice == "Anthropic":
        provider_name = "anthropic"
        model_display = os.getenv("ANTHROPIC_MODEL")
        MAX_TURNS = 8 if active_skill_name == "long_running_autonomous" else 5

    else:  # Ollama
        provider_name = "ollama"
        model_display = os.getenv("OLLAMA_MODEL")
        MAX_TURNS = 6 if active_skill_name == "long_running_autonomous" else 4

    messages, current_version = _prepare_messages(history, message, provider_name)
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
                yield history + [{"role": "user", "content": message}, {"role": "assistant", "content": f"❌ MCP Error: {result['error']}"}]
                return

            content = result.get("content", "") or ""
            tool_calls = result.get("tool_calls", []) or []

            if tool_calls:
                messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})

                tool_names = []
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
                        tool_names.append(tool_name)
                        tool_steps.append(f"🔧 `{tool_name}`")
                        tool_result = call_mcp_tool(tool_name, args)
                        messages.append({"role": "tool", "content": tool_result, "tool_call_id": tc.get("id", "")})

                current_history = history + [{"role": "user", "content": message}]

                if tool_names:
                    for i in range(12):
                        status_msg = _build_tool_status_message(model_display, context_line, tool_names, i)
                        yield current_history + [{"role": "assistant", "content": status_msg}]
                        import time
                        time.sleep(0.20)
                else:
                    yield current_history + [{"role": "assistant", "content": f"**{model_display}**\n*{context_line}*\n\n🔧 Verarbeite Tools ..."}]

                continue

            # Finale Antwort
            final_msg = f"**{model_display}**"
            if context_line:
                final_msg += f"\n*{context_line}*"
            final_msg += f"\n\n{content or ''}"
            if tool_steps:
                final_msg += "\n\n" + "\n".join(tool_steps)

            # Sauberes Speichern mit Tool-Marker (über Hilfsfunktion)
            _save_final_assistant_message(
                content=content,
                tool_steps=tool_steps,
                tool_calls=tool_calls,
                context_line=context_line
            )

            base_history = history + [{"role": "user", "content": message}]
            for partial in _stream_final_answer(base_history, final_msg):
                yield partial
            return

        except Exception as e:
            yield history + [{"role": "user", "content": message}, {"role": "assistant", "content": f"Error: {str(e)}"}]
            return

    yield history + [{"role": "user", "content": message}, {"role": "assistant", "content": "Max tool turns reached."}]


def chat_with_agent(message: str, history: list, model_choice: str):
    final_result = None
    for partial_history in _chat_with_agent_generator(message, history, model_choice):
        final_result = partial_history
    return final_result


# ====================== STREAMING ======================
def chat_with_agent_streaming(message: str, history: list, model_choice: str):
    import time

    if model_choice == "xAI":
        provider_name = "xai"
        model_display = os.getenv("XAI_MODEL")
        MAX_TURNS = 6
    elif model_choice == "OpenAI":
        provider_name = "openai"
        model_display = os.getenv("OPENAI_MODEL")
        MAX_TURNS = 6
    elif model_choice == "Anthropic":
        provider_name = "anthropic"
        model_display = os.getenv("ANTHROPIC_MODEL")
        MAX_TURNS = 5
    else:
        provider_name = "ollama"
        model_display = os.getenv("OLLAMA_MODEL")
        MAX_TURNS = 4

    messages, _ = _prepare_messages(history, message, provider_name)
    context_line = _get_context_line()

    chat_history = history + [{"role": "user", "content": message}]
    yield chat_history

    url = "http://mcp-server:8321/mcp/stream"
    payload = {
        "params": {
            "provider": provider_name,
            "messages": messages,
            "temperature": 0.7
        }
    }

    full_response = ""
    chunk_buffer = ""
    update_every = 5
    assistant_index = None

    try:
        with httpx.stream("POST", url, json=payload, timeout=120.0) as response:
            for line in response.iter_lines():
                if not line:
                    continue

                line_str = line.decode("utf-8") if isinstance(line, bytes) else line

                if line_str.startswith("data: "):
                    content = line_str[6:]

                    if content == "[DONE]":
                        break
                    if content.startswith("[ERROR]"):
                        full_response += f"\n\n❌ {content}"
                        break

                    full_response += content
                    chunk_buffer += content

                    if assistant_index is None:
                        chat_history.append({"role": "assistant", "content": ""})
                        assistant_index = len(chat_history) - 1

                    if (len(chunk_buffer) >= update_every or 
                        content.endswith((" ", "\n", ".", "!", "?", ":", ";"))):

                        display_content = full_response
                        if context_line:
                            display_content = f"**{model_display}**\n*{context_line}*\n\n{full_response}"

                        chat_history[assistant_index]["content"] = display_content + "▌"
                        yield chat_history
                        chunk_buffer = ""
                        time.sleep(0.012)

        final_content = full_response
        if context_line:
            final_content = f"**{model_display}**\n*{context_line}*\n\n{full_response}"

        if assistant_index is not None:
            chat_history[assistant_index]["content"] = final_content
        else:
            chat_history.append({"role": "assistant", "content": final_content})

        yield chat_history

    except Exception as e:
        error_msg = f"❌ Streaming Fehler: {str(e)}"
        if assistant_index is not None:
            chat_history[assistant_index]["content"] = error_msg
        else:
            chat_history.append({"role": "assistant", "content": error_msg})
        yield chat_history


# ====================== STATUS & REFRESH ======================
def get_status(model_choice_value: str = "xAI"):
    try:
        persona_result = call_mcp_tool("get_active_persona", {})
        persona_name = "None"
        if isinstance(persona_result, str):
            try:
                data = json.loads(persona_result)
                if isinstance(data, dict) and "name" in data:
                    persona_name = data.get("name", "None")
            except:
                pass

        skill_result = call_mcp_tool("get_active_skill", {})
        skill_name = "None"
        if isinstance(skill_result, str):
            try:
                data = json.loads(skill_result)
                if isinstance(data, dict) and "name" in data:
                    skill_name = data.get("name", "None")
            except:
                pass

        provider_result = call_mcp_tool("get_active_provider", {})
        provider = "xai"
        if isinstance(provider_result, str):
            try:
                data = json.loads(provider_result)
                if isinstance(data, dict):
                    provider = data.get("active_provider", "xai")
            except:
                pass

        model_map = {"xAI": "xai", "OpenAI": "openai", "Anthropic": "anthropic", "Ollama": "ollama"}
        model_for_prompt = model_map.get(model_choice_value, "xai")
        prompt_data = mcp_jsonrpc("prompts/get_dynamic", {"model": model_for_prompt})
        version = prompt_data.get("version", "unknown") if prompt_data else "unknown"

        try:
            tools = get_mcp_tools()
            tool_count = len(tools) if tools else 0
        except:
            tool_count = 0

        return (
            f"✅ Connected • {tool_count} tools",
            f"📜 Prompt: {version}",
            f"🎭 Persona: {persona_name}",
            f"🛠️ Skill: {skill_name}"
        )

    except Exception as e:
        return (
            f"❌ Error: {str(e)}",
            "📜 Prompt: error",
            "🎭 Persona: error",
            "🛠️ Skill: error"
        )


def refresh_all(model_choice_value: str):
    return get_status(model_choice_value)


def refresh_ui_state(model_choice_value: str = "xAI"):
    status = get_status(model_choice_value)

    try:
        session_result = call_mcp_tool("get_active_session", {})
        if isinstance(session_result, str):
            session_data = json.loads(session_result)
            session_text = f"📍 Session: {session_data.get('session_id', '?')} ({session_data.get('name', 'default')})"
        else:
            session_text = "📍 Session: ?"
    except:
        session_text = "📍 Session: error"

    try:
        prompt_text = get_system_prompt(model_choice_value)
    except:
        prompt_text = "❌ Konnte Prompt nicht laden"

    # === NEU: Model aus Backend lesen (Single Source of Truth) ===
    model_value = model_choice_value
    try:
        provider_result = call_mcp_tool("get_active_provider", {})
        if isinstance(provider_result, str):
            data = json.loads(provider_result)
            provider = data.get("active_provider", "xai").lower()

            mapping = {
                "xai": "xAI",
                "openai": "OpenAI",
                "anthropic": "Anthropic",
                "ollama": "Ollama",
            }
            model_value = mapping.get(provider, "xAI")
    except Exception:
        pass  # Fallback auf mitgegebenen Wert

    return (
        status[0],
        status[1],
        status[2],
        status[3],
        session_text,
        model_value,
        prompt_text
    )


def respond(user_message, chat_history, model):
    if not user_message or not user_message.strip():
        return chat_history, ""

    try:
        call_mcp_tool("add_chat_turn", {"role": "user", "content": user_message})

        temp_history = chat_history + [{"role": "user", "content": user_message}]
        yield temp_history, ""

        final_history = None
        for partial_history in _chat_with_agent_generator(user_message, chat_history, model):
            final_history = partial_history
            yield partial_history, ""

        if final_history is None:
            yield temp_history, ""
            return temp_history, ""

        return final_history, ""

    except Exception as e:
        error_history = (chat_history or []) + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": f"❌ Fehler: {str(e)}"}
        ]
        yield error_history, ""
        return error_history, ""