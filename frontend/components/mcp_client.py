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


def mcp_jsonrpc(method: str, params: dict = None):
    """Führt einen JSON-RPC Aufruf gegen den MCP Server aus."""
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
        return {"error": "❌ MCP Server nicht erreichbar"}
    except requests.exceptions.Timeout:
        return {"error": "⏱️ MCP Server Timeout"}
    except Exception as e:
        return {"error": f"❌ Unerwarteter Fehler: {str(e)}"}


def call_mcp_tool(tool_name: str, arguments: dict = None):
    """Ruft ein Tool über den MCP Server auf."""
    result = mcp_jsonrpc("tools/call", {"name": tool_name, "arguments": arguments or {}})
    
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