#!/usr/bin/env python3
"""
mcp_client.py - Zentrale MCP-Kommunikationsschicht für das Frontend

Single Source of Truth für alle JSON-RPC Aufrufe aus der UI.
Wird von allen Komponenten und dem chat_handler importiert.
"""

import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

MCP_URL = os.getenv("MCP_PUBLIC_URL")


import time
import requests
from typing import Any, Dict, Optional

MCP_URL = os.getenv("MCP_PUBLIC_URL")


def mcp_jsonrpc(method: str, params: dict = None, request_id: int = 1, max_retries: int = 4) -> Any:
    """JSON-RPC Aufruf mit Retry bei transienten Fehlern."""
    url = f"{MCP_URL.rstrip('/')}/mcp"
    payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}

    last_exception = None

    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("error"):
                err = data["error"]
                # Bei echten Server-Fehlern nicht endlos retryen
                if isinstance(err, dict) and err.get("code") in [-32603, -32602]:
                    return {"error": err.get("message", str(err))}
                return {"error": str(err)}

            return data.get("result")

        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout) as e:
            last_exception = e
            wait_time = min(2 ** attempt, 8)  # 1s, 2s, 4s, 8s
            print(f"[MCP Retry] Versuch {attempt + 1}/{max_retries} fehlgeschlagen ({type(e).__name__}). Warte {wait_time}s...")
            time.sleep(wait_time)
            continue

        except Exception as e:
            # Bei anderen Fehlern nicht retryen
            return {"error": f"Unexpected error: {str(e)}"}

    # Nach allen Retries fehlgeschlagen
    return {"error": f"MCP connection failed after {max_retries} retries. Last error: {last_exception}"}


def call_mcp_tool(tool_name: str, arguments: dict = None, max_retries: int = 3) -> str:
    """Tool-Aufruf mit Retry."""
    result = mcp_jsonrpc("tools/call", {
        "name": tool_name,
        "arguments": arguments or {}
    }, max_retries=max_retries)

    if isinstance(result, dict) and "error" in result:
        return f"Error: {result['error']}"

    if result and "content" in result:
        texts = [item.get("text", "") for item in result["content"] if item.get("type") == "text"]
        return "\n".join(texts)

    return "No result returned"


def get_mcp_tools():
    """Holt die Liste aller verfügbaren Tools."""
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