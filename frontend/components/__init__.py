"""
frontend/components/__init__.py
Zentrale Import-Datei für alle UI-Komponenten des MCP Agent Frontends.

Alle Komponenten sind reine UI-Module und kommunizieren ausschließlich
über die MCP JSON-RPC Schnittstelle (mcp_jsonrpc / call_mcp_tool).
"""

from .status_bar import create_status_bar
from .prompt_viewer import create_prompt_viewer, get_system_prompt
from .persona_control import create_persona_control
from .skill_control import create_skill_control
from .tools_panel import create_tools_panel
from .memory_panel import create_memory_panel

__all__ = [
    "create_status_bar",
    "create_prompt_viewer",
    "get_system_prompt",
    "create_persona_control",
    "create_skill_control",
    "create_tools_panel",
    "create_memory_panel"
]
