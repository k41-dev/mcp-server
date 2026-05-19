"""
frontend/components/__init__.py
Zentrale Import-Datei für alle UI-Komponenten des MCP Agent Frontends.

Alle Komponenten sind reine UI-Module und kommunizieren ausschließlich
über die MCP JSON-RPC Schnittstelle (mcp_jsonrpc / call_mcp_tool).
"""

from .status_bar import create_status_bar
from .prompt_viewer import create_prompt_viewer, get_system_prompt

__all__ = [
    "create_status_bar",
    "create_prompt_viewer",
    "get_system_prompt"
]
