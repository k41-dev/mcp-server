#!/usr/bin/env python3
"""
client.py
CLI tool to:
  - Call Grok/Ollama via the official XAI API/Localhost
  - Interact with the running MCP-Server container (localhost:8321/mcp)

Features:
  • Dynamic agent system prompt loaded from prompts/system_agent_xxx.md
  • Live tool descriptions injected into prompt for superior reasoning
  • Full multi-turn tool-calling agent loop with Grok/Ollama
  • Optional streaming mode (--stream) for real-time token output

Usage examples:
  uv run client.py grok "What is the current server status and UTC time?"
  uv run client.py ollama "What's the current UTC time and latest AI news?"
  uv run client.py mcp-list
  uv run client.py mcp-call get_server_info
"""

import os
import sys
import json
import argparse
import requests
from dotenv import load_dotenv
from openai import OpenAI
from types import SimpleNamespace

load_dotenv()

XAI_API_KEY = os.getenv("XAI_API_KEY")
XAI_MODEL = os.getenv("XAI_MODEL")

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
OLLAMA_HOST = os.getenv("OLLAMA_HOST")

MCP_PUBLIC_URL = os.getenv("MCP_PUBLIC_URL")

if not XAI_API_KEY:
    print("❌ XAI_API_KEY not found in .env")
    sys.exit(1)

client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")


# ====================== MCP COMMUNICATION ======================
def mcp_jsonrpc(method: str, params: dict = None, request_id: int = 1):
    url = f"{MCP_PUBLIC_URL.rstrip('/')}/mcp"
    payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("error") is not None:
            print(f"❌ MCP Error: {data['error']}")
            return None
        return data.get("result")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to reach MCP server at {url}: {e}")
        return None


def get_mcp_tools():
    """Fetch all tools from MCP server and convert to OpenAI format"""
    result = mcp_jsonrpc("tools/list")
    if not result or "tools" not in result:
        return []
    
    openai_tools = []
    for tool in result["tools"]:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["inputSchema"]
            }
        })
    return openai_tools


def call_mcp_tool(tool_name: str, arguments: dict):
    """Execute a tool via the MCP server"""
    params = {"name": tool_name, "arguments": arguments or {}}
    result = mcp_jsonrpc("tools/call", params)
    if result and "content" in result:
        texts = [item["text"] for item in result["content"] if item.get("type") == "text"]
        return "\n".join(texts)
    return "No result returned"

# ====================== CHAT HISTORY VIA MCP (reiner Client) ======================
def load_recent_chat_history(limit: int = 10) -> list:
    """Lädt die letzten Chat-Nachrichten über den MCP-Server."""
    result = call_mcp_tool("list_chat_history", {"limit": limit})
    return result if isinstance(result, str) else ""


def save_chat_turn(role: str, content: str):
    """Speichert einen Chat-Turn über den MCP-Server."""
    if role not in ("user", "assistant") or not content:
        return
    call_mcp_tool("add_chat_turn", {"role": role, "content": content})

def recall_long_term_memories(query: str = "", limit: int = 5) -> str:
    """Ruft semantische Langzeit-Memories über den MCP-Server ab."""
    result = call_mcp_tool("recall_memory", {
        "query": query,
        "limit": limit
    })
    return result if isinstance(result, str) else ""

def get_dynamic_system_prompt(model: str = "grok") -> str:
    result = mcp_jsonrpc("prompts/get_dynamic", {"model": model})
    if result and isinstance(result, dict) and "prompt" in result:
        return result["prompt"]
    
    print("⚠️  Konnte keinen dynamischen Prompt vom Server holen. Verwende minimalen Fallback.")
    return "You are a helpful AI agent with access to MCP tools."

# ====================== GROK AGENT WITH TOOLS ======================
def run_grok_agent(query: str, max_turns: int = 10, stream: bool = False):
    """Run Grok with full access to all MCP tools + dynamic agent prompt."""
    tools = get_mcp_tools()

    if not tools:
        print("❌ Could not load tools from MCP server")
        return

    print(f"🔧 Loaded {len(tools)} MCP tools for Grok\n")

    # ====================== CHAT HISTORY VIA MCP ======================
    print("🧠 Chat History wird über MCP geladen...")
    history_text = load_recent_chat_history(limit=10)
    if history_text and "No chat history" not in history_text:
        print("   📜 Chat History vom Server geladen")
    else:
        print("   🆕 Fresh start — keine Chat History vorhanden")

    memories_text = recall_long_term_memories(query=query, limit=5)
    if memories_text and "No relevant memories" not in memories_text:
        print("   🧠 Long-Term Memories geladen")

    system_prompt = get_dynamic_system_prompt("grok")
    messages = [{"role": "system", "content": system_prompt}]

    if history_text and "No chat history" not in history_text:
        messages.append({
            "role": "system",
            "content": f"Recent conversation history from server:\n{history_text}"
        })

    if memories_text and "No relevant memories" not in memories_text:
        messages.append({
            "role": "system",
            "content": f"Relevant long-term memories about the user:\n{memories_text}"
        })

    messages.append({"role": "user", "content": query})
    save_chat_turn("user", query)

    for turn in range(max_turns):
        if stream:
            # ========== STREAMING PATH ==========
            response_stream = client.chat.completions.create(
                model=XAI_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.7,
                stream=True,
            )

            content = ""
            tool_call_accumulator = {}

            for chunk in response_stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                if delta.content:
                    content += delta.content

                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_call_accumulator:
                            tool_call_accumulator[idx] = {"id": tc_delta.id, "name": "", "arguments": ""}
                        if tc_delta.function:
                            if tc_delta.function.name:
                                tool_call_accumulator[idx]["name"] = tc_delta.function.name
                            if tc_delta.function.arguments:
                                tool_call_accumulator[idx]["arguments"] += tc_delta.function.arguments

            msg = SimpleNamespace(content=content, tool_calls=None)
            if tool_call_accumulator:
                msg.tool_calls = []
                for tc in tool_call_accumulator.values():
                    if tc["name"]:
                        func = SimpleNamespace(name=tc["name"], arguments=tc["arguments"])
                        tool_call = SimpleNamespace(id=tc["id"], function=func)
                        msg.tool_calls.append(tool_call)
        else:
            # ========== NON-STREAMING PATH ==========
            response = client.chat.completions.create(
                model=XAI_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.7,
            )
            msg = response.choices[0].message

        # ====================== TOOL CALL HANDLING ======================
        tool_calls = getattr(msg, "tool_calls", None) or []

        if not tool_calls:
            # === Final Answer ===
            content = getattr(msg, "content", "") or ""
            print(f"\n🤖 {XAI_MODEL}:")
            print(content)

            if content:
                save_chat_turn("assistant", content)
            return

        # === Tool Calls vorhanden ===
        if hasattr(msg, "model_dump"):
            messages.append(msg.model_dump(exclude_none=True))
        else:
            messages.append({"role": "assistant", "content": getattr(msg, "content", None)})

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")
            print(f"🔨 {XAI_MODEL} called: {tool_name}({args})")

            result = call_mcp_tool(tool_name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

    # Nur erreichen, wenn die Schleife ohne finale Antwort durchgelaufen ist
    print("\n⚠️ Reached max turns without final answer")


# ====================== OLLAMA AGENT ======================
def run_ollama_agent(query: str, model: str = None, stream: bool = True, max_turns: int = 8):
    """Full agent loop for local Ollama models with MCP tools + memory."""
    model = model or OLLAMA_MODEL
    ollama_host = OLLAMA_HOST

    try:
        import ollama
    except ImportError:
        print("❌ 'ollama' Python package not found. Run: uv add ollama")
        return

    # Setup Ollama client
    try:
        ollama_client = ollama.Client(host=ollama_host)
        ollama_client.list()
    except Exception as e:
        print(f"❌ Cannot connect to Ollama at {ollama_host}: {e}")
        print("   Make sure Ollama is running and the model is pulled.")
        return

    tools = get_mcp_tools()
    if tools:
        print(f"🔧 Loaded {len(tools)} MCP tools for Ollama\n")
    else:
        print("⚠️ No MCP tools loaded — running in plain chat mode\n")

    # ====================== MEMORY + SESSION (reiner Client) ======================
    print("🧠 Chat History wird über MCP geladen...")
    history_text = load_recent_chat_history(limit=10)
    if history_text and "No chat history" not in history_text:
        print("   📜 Chat History vom Server geladen")
    else:
        print("   🆕 Fresh start — keine Chat History vorhanden")

    memories_text = recall_long_term_memories(query=query, limit=5)

    system_prompt = get_dynamic_system_prompt("ollama")
    messages = [{"role": "system", "content": system_prompt}]

    if memories_text and "No relevant memories" not in memories_text:
        messages.append({
            "role": "system",
            "content": f"Relevant long-term memories about the user:\n{memories_text}"
        })

    if history_text and "No chat history" not in history_text:
        messages.append({
            "role": "system",
            "content": f"Recent conversation history from server:\n{history_text}"
        })

    messages.append({"role": "user", "content": query})
    save_chat_turn("user", query)

    # ====================== AGENT LOOP ======================
    for turn in range(max_turns):
        try:
            content = ""
            tool_calls = []

            if stream:
                # --- STREAMING ---
                tool_call_accumulator = {}
                stream_resp = ollama_client.chat(
                    model=model,
                    messages=messages,
                    tools=tools if tools else None,
                    stream=True
                )

                for chunk in stream_resp:
                    msg = chunk.get("message", {})
                    if msg.get("content"):
                        content += msg["content"]

                    if msg.get("tool_calls"):
                        for tc in msg["tool_calls"]:
                            idx = tc.get("index", 0)
                            if idx not in tool_call_accumulator:
                                tool_call_accumulator[idx] = {
                                    "id": tc.get("id", f"call_{idx}"),
                                    "name": "",
                                    "arguments": ""
                                }
                            func = tc.get("function", {})
                            if func.get("name"):
                                tool_call_accumulator[idx]["name"] = func["name"]
                            arg_value = func.get("arguments", "")
                            if isinstance(arg_value, dict):
                                arg_value = json.dumps(arg_value)
                            if arg_value:
                                tool_call_accumulator[idx]["arguments"] += arg_value

                # Reconstruct final message
                final_msg = {"role": "assistant", "content": content}
                if tool_call_accumulator:
                    final_msg["tool_calls"] = []
                    for tc in tool_call_accumulator.values():
                        if tc["name"]:
                            try:
                                args_dict = json.loads(tc["arguments"] or "{}")
                            except:
                                args_dict = {}
                            final_msg["tool_calls"].append({
                                "id": tc["id"],
                                "function": {"name": tc["name"], "arguments": args_dict}
                            })
                    tool_calls = final_msg.get("tool_calls", [])
            else:
                # --- NON-STREAMING ---
                resp = ollama_client.chat(
                    model=model,
                    messages=messages,
                    tools=tools if tools else None
                )
                final_msg = resp.get("message", {})
                content = final_msg.get("content", "") or ""
                tool_calls = final_msg.get("tool_calls", []) or []

            # === Fallback: Raw JSON Tool Call Detection (defensiv wie in gradio_app.py) ===
            if not tool_calls and isinstance(content, str) and content.strip().startswith("{"):
                try:
                    parsed = json.loads(content.strip())
                    if isinstance(parsed, dict) and parsed.get("name"):
                        tool_calls = [{
                            "id": f"fallback_{turn}",
                            "function": {
                                "name": parsed.get("name"),
                                "arguments": parsed.get("parameters") or parsed.get("arguments") or {}
                            }
                        }]
                        content = ""  # rohes JSON ausblenden
                        print(f"🔧 Detected raw JSON tool call → executing {parsed['name']}")
                        final_msg = {"role": "assistant", "content": content, "tool_calls": tool_calls}
                except Exception:
                    pass

            # Append assistant message to history
            messages.append(final_msg)

            # === Tool Calls vorhanden? ===
            if tool_calls:
                for tool_call in tool_calls:
                    func = tool_call.get("function", {})
                    tool_name = func.get("name")
                    if not tool_name:
                        continue

                    try:
                        args = json.loads(func.get("arguments", "{}")) if isinstance(func.get("arguments"), str) else func.get("arguments", {})
                    except:
                        args = {}

                    print(f"🔨 {model} called: {tool_name}({args})")
                    result = call_mcp_tool(tool_name, args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "content": result
                    })

                continue  # nächste Runde für finale Antwort

            # === Finale Antwort ===
            if content.strip():
                save_chat_turn("assistant", content.strip())

            print(f"\n🤖 {model}:")
            if content:
                print(content)
            return

        except Exception as e:
            print(f"\n❌ Ollama error on turn {turn}: {e}")
            break

    print("\n⚠️ Reached max turns without final answer")

# ====================== CLI ======================
def main():
    parser = argparse.ArgumentParser(description="MCP Tools Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    grok_parser = subparsers.add_parser("grok", help="Chat with AI using all MCP tools")
    grok_parser.add_argument("query", nargs="+", help="Your question")
    grok_parser.add_argument("--stream", action="store_true", help="Stream tokens live (default: off)")

    ollama_parser = subparsers.add_parser("ollama", help="Chat with local Ollama model (with memory context)")
    ollama_parser.add_argument("query", nargs="+", help="Your question to the local model")
    ollama_parser.add_argument("--model", help="Override model name (e.g. llama3.2, gemma2:2b)")
    ollama_parser.add_argument("--stream", action="store_true", help="Stream tokens live (default: off)")
    ollama_parser.add_argument("--no-stream", action="store_true", help="Disable streaming output (overrides --stream)")

    subparsers.add_parser("mcp-list", help="List MCP tools")
    call_parser = subparsers.add_parser("mcp-call", help="Directly call an MCP tool")
    call_parser.add_argument("tool_name", help="Tool name")
    call_parser.add_argument("--args", type=str, help='JSON args, e.g. \'{"city": "Berlin"}\'')

    args = parser.parse_args()

    if args.command == "grok":
        query = " ".join(args.query)
        run_grok_agent(query, stream=getattr(args, "stream", False))
    elif args.command == "ollama":
        query = " ".join(args.query)
        run_ollama_agent(query, model=getattr(args, "model", None), stream=not getattr(args, "no_stream", False))
    elif args.command == "mcp-list":
        result = mcp_jsonrpc("tools/list")
        if result and "tools" in result:
            print("✅ Available MCP Tools:")
            for t in result["tools"]:
                print(f"  • {t['name']}: {t['description']}")
    elif args.command == "mcp-call":
        tool_args = json.loads(args.args) if args.args else None
        result = call_mcp_tool(args.tool_name, tool_args)
        print(result)


if __name__ == "__main__":
    main()