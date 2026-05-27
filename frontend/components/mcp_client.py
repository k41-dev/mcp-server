#!/usr/bin/env python3
"""
mcp_client.py - Zentrale MCP-Kommunikationsschicht für das Frontend

Single Source of Truth für alle JSON-RPC Aufrufe aus der UI.
Wird von allen Komponenten und dem chat_handler importiert.
"""

import os
import time
import json
import requests
from dotenv import load_dotenv
from typing import Any, Dict, Optional

load_dotenv()

MCP_URL = os.getenv("MCP_PUBLIC_URL")


def mcp_jsonrpc(
    method: str, 
    params: Optional[Dict] = None, 
    request_id: int = 1, 
    max_retries: int = 2
) -> Any:
    """
    Führt einen JSON-RPC Aufruf gegen den MCP Server aus.
    Mit leichtem Retry bei transienten Netzwerkfehlern.
    """
    if not MCP_URL:
        return {"error": "MCP_PUBLIC_URL ist nicht gesetzt"}

    url = f"{MCP_URL.rstrip('/')}/mcp"
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or {}
    }

    last_exception = None

    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=25)
            response.raise_for_status()
            data = response.json()

            if data.get("error"):
                err = data["error"]
                if isinstance(err, dict):
                    return {"error": err.get("message", str(err))}
                return {"error": str(err)}

            return data.get("result")

        except (requests.exceptions.Timeout, 
                requests.exceptions.ConnectionError, 
                requests.exceptions.ReadTimeout) as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = min(2 ** attempt, 4)  # max 4 Sekunden
                print(f"[MCP Retry] Versuch {attempt + 1}/{max_retries} fehlgeschlagen. Warte {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                return {"error": f"MCP Timeout nach {max_retries} Versuchen"}

        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    return {"error": f"MCP connection failed. Last error: {last_exception}"}


def call_mcp_tool(tool_name: str, arguments: Optional[Dict] = None) -> str:
    """
    Ruft ein Tool über den MCP Server auf.
    Gibt das Ergebnis als String zurück oder eine Fehlermeldung.
    """
    result = mcp_jsonrpc("tools/call", {
        "name": tool_name,
        "arguments": arguments or {}
    })

    if isinstance(result, dict) and "error" in result:
        return f"Error: {result['error']}"

    if result and isinstance(result, dict) and "content" in result:
        texts = [
            item.get("text", "") 
            for item in result["content"] 
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        return "\n".join(texts)

    return "No result returned"


def get_mcp_tools():
    """Holt die Liste aller verfügbaren Tools vom MCP Server."""
    result = mcp_jsonrpc("tools/list")

    if result and isinstance(result, dict) and "tools" in result:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("inputSchema", {})
                }
            }
            for tool in result["tools"]
        ]
    return []