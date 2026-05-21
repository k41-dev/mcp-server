#!/usr/bin/env python3
"""
chat_handler.py - Zentrale Chat-Logik für das Frontend (als Komponente)
"""

import os
import json
import httpx
from .mcp_client import mcp_jsonrpc, call_mcp_tool, get_mcp_tools


XAI_API_KEY = os.getenv("XAI_API_KEY")
XAI_MODEL = os.getenv("XAI_MODEL")
OLLAMA_URL = os.getenv("OLLAMA_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")


# ====================== HELPER ======================
def _get_context_line() -> str:
    """Holt aktive Persona + Skill und baut die einheitliche Context-Line."""
    active_persona_name = "None"
    active_skill_name = "None"

    try:
        persona_result = call_mcp_tool("get_active_persona", {})
        if isinstance(persona_result, str) and "name" in persona_result:
            p = json.loads(persona_result)
            active_persona_name = p.get("name", "None")
    except Exception:
        pass

    try:
        skill_result = call_mcp_tool("get_active_skill", {})
        if isinstance(skill_result, str) and "name" in skill_result:
            s = json.loads(skill_result)
            active_skill_name = s.get("name", "None")
    except Exception:
        pass

    context_parts = []
    if active_persona_name and active_persona_name != "None":
        context_parts.append(f"🎭 {active_persona_name}")
    if active_skill_name and active_skill_name != "None":
        context_parts.append(f"🛠️ {active_skill_name}")

    return " • ".join(context_parts) if context_parts else ""


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


# ====================== CORE AGENT (als Generator) ======================
def _chat_with_agent_generator(message: str, history: list, model_choice: str):
    """
    Generator-Version des Agenten.
    Yieldet nach jedem Tool-Durchlauf den aktuellen History-Stand.
    Am Ende yielded sie das finale Ergebnis.
    """
    tools = get_mcp_tools()
    clean_history = _sanitize_history(history)

    is_grok = model_choice == "Grok"
    provider_name = "grok" if is_grok else "ollama"
    model_display = XAI_MODEL if is_grok else OLLAMA_MODEL

    # System Prompt
    prompt_data = mcp_jsonrpc("prompts/get_dynamic", {"model": provider_name})
    system_prompt = prompt_data.get("prompt", "") if prompt_data else ""
    current_version = prompt_data.get("version", "v1") if prompt_data else "v1"

    if not hasattr(_chat_with_agent_generator, "_last_prompt_version"):
        _chat_with_agent_generator._last_prompt_version = None

    include_system = (len(clean_history) == 0 or current_version != _chat_with_agent_generator._last_prompt_version)
    if include_system:
        messages = [{"role": "system", "content": system_prompt}] + clean_history + [{"role": "user", "content": message}]
        _chat_with_agent_generator._last_prompt_version = current_version
    else:
        messages = clean_history + [{"role": "user", "content": message}]

    context_line = _get_context_line()
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
                yield history + [{"role": "user", "content": message}, {"role": "assistant", "content": f"❌ MCP Error: {result['error']}"}]
                return

            content = result.get("content", "") or ""
            tool_calls = result.get("tool_calls", []) or []

            if tool_calls:
                # Tool-Calls vorhanden → Messages erweitern und Tools ausführen
                messages.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls
                })

                # === Tool-Namen für die Anzeige sammeln ===
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
                        messages.append({
                            "role": "tool",
                            "content": tool_result,
                            "tool_call_id": tc.get("id", "")
                        })

                # === Bessere Live-Darstellung mit Aktivitäts-Indikator ===
                current_history = history + [{"role": "user", "content": message}]

                if tool_names:
                    tool_list = ", ".join([f"`{name}`" for name in tool_names])

                    # Guter rotierender Spinner (Braille-Style)
                    spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

                    for i in range(12):   # 12 Frames = ca. 2,4 Sekunden Animation
                        frame = spinner_frames[i % len(spinner_frames)]

                        status_msg = (
                            f"{model_display}\n"
                            f"{context_line}\n\n"
                            f"{frame}  Führe Tool(s) aus: {tool_list}"
                        )

                        yield current_history + [{"role": "assistant", "content": status_msg}]
                        import time
                        time.sleep(0.20)   # Etwas schnelleres Rotieren

                else:
                    status_msg = f"**{model_display}**\n*{context_line}*\n\n🔧 Verarbeite Tools ..."
                    yield current_history + [{"role": "assistant", "content": status_msg}]

                continue

            # === Keine Tool-Calls mehr → Finale Antwort ===
            final_msg = f"**{model_display}**"
            if context_line:
                final_msg += f"\n*{context_line}*"
            final_msg += f"\n\n{content or ''}"
            if tool_steps:
                final_msg += "\n\n" + "\n".join(tool_steps)

            if content:
                call_mcp_tool("add_chat_turn", {"role": "assistant", "content": content})

            final_history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": final_msg}]
            yield final_history
            return

        except Exception as e:
            error_history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": f"Error: {str(e)}"}]
            yield error_history
            return

    # Max turns reached
    final_history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": "Max tool turns reached."}]
    yield final_history


# ====================== WRAPPER (für Backward-Compatibility) ======================
def chat_with_agent(message: str, history: list, model_choice: str):
    """
    Kompatibilitäts-Wrapper.
    Nutzt den Generator intern und gibt nur das finale Ergebnis zurück.
    Bestehende Aufrufe funktionieren weiterhin ohne Änderung.
    """
    final_result = None
    for partial_history in _chat_with_agent_generator(message, history, model_choice):
        final_result = partial_history
    return final_result


# ====================== CORE STREAMING LOGIC ======================
def chat_with_agent_streaming(message: str, history: list, model_choice: str):
    """
    Streaming-Pfad (aktuell text-only, ohne Tool-Calling).
    Sauberes sofortiges User-Message + inkrementelles Streaming der Assistant-Antwort.
    """
    import time

    is_grok = model_choice == "Grok"
    model_display = XAI_MODEL if is_grok else OLLAMA_MODEL
    provider_name = "grok" if is_grok else "ollama"

    # System Prompt
    prompt_data = mcp_jsonrpc("prompts/get_dynamic", {"model": provider_name})
    system_prompt = prompt_data.get("prompt", "") if prompt_data else ""

    clean_history = _sanitize_history(history)
    messages = [{"role": "system", "content": system_prompt}] + clean_history + [{"role": "user", "content": message}]

    context_line = _get_context_line()

    # === 1. Yield: Nur User-Message (sofort sichtbar) ===
    chat_history = history + [{"role": "user", "content": message}]
    yield chat_history

    # Streaming vorbereiten
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

                    # Assistant-Message beim ersten Chunk hinzufügen
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

        # === Finaler Yield ohne Cursor ===
        final_content = full_response
        if context_line:
            final_content = f"**{model_display}**\n*{context_line}*\n\n{full_response}"

        if assistant_index is not None:
            chat_history[assistant_index]["content"] = final_content
        else:
            # Falls aus irgendeinem Grund kein Chunk kam
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
    """
    Hybrid-Modus mit sofortiger User-Message + ohne Duplizierung
    """
    if not user_message or not user_message.strip():
        return chat_history, ""

    # User-Message sofort persistieren
    call_mcp_tool("add_chat_turn", {"role": "user", "content": user_message})

    # === Sofortige Anzeige der User-Message (nur für die UI) ===
    temp_history = chat_history + [{"role": "user", "content": user_message}]
    yield temp_history, ""

    try:
        final_history = None

        # Generator mit ORIGINALER History starten (nicht mit temp_history!)
        for partial_history in _chat_with_agent_generator(user_message, chat_history, model):
            final_history = partial_history
            yield partial_history, ""

        if final_history is None:
            yield temp_history, ""
            return temp_history, ""

        return final_history, ""

    except Exception as e:
        error_history = temp_history + [
            {"role": "assistant", "content": f"❌ Fehler im Hybrid-Modus: {str(e)}"}
        ]
        yield error_history, ""
        return error_history, ""