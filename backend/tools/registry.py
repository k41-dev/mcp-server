#!/usr/bin/env python3
"""
registry.py - Tool Factory & Registry (Single Source of Truth)
"""

import json
from pathlib import Path
from typing import Dict, Any, Callable, Optional, List
from pydantic import BaseModel
import logging


logger = logging.getLogger("mcp.tools")


class ToolDefinition(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]
    category: str = "core"


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._executors: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}


    def register(
        self,
        definition: ToolDefinition,
        executor: Callable[[Dict[str, Any]], Dict[str, Any]]
    ):
        """Registriert ein Tool mit Definition und Ausführungsfunktion."""
        self._tools[definition.name] = definition
        self._executors[definition.name] = executor


    def get_definition(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)


    def get_all_definitions(self) -> List[ToolDefinition]:
        return list(self._tools.values())


    def execute(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Führt ein Tool aus und loggt den Aufruf."""
        # === Tool Call Logging ===
        arg_preview = str(args)[:120] + "..." if len(str(args)) > 120 else str(args)
        logger.info(f"🔧 Tool aufgerufen: {name} | Args: {arg_preview}")

        if name not in self._executors:
            logger.warning(f"❌ Unbekanntes Tool: {name}")
            return {
                "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                "isError": True
            }

        try:
            result = self._executors[name](args)
            is_error = result.get("isError", False)
            status = "❌ Fehler" if is_error else "✅ Erfolg"
            logger.info(f"{status} | Tool: {name}")
            return result
        except Exception as e:
            logger.error(f"💥 Exception beim Tool '{name}': {str(e)}")
            return {
                "content": [{"type": "text", "text": f"Tool execution error: {str(e)}"}],
                "isError": True
            }


    def validate(self) -> None:
        """Stellt sicher, dass jede Definition einen Executor hat.
        
        Wird idealerweise direkt nach dem Laden der Definitionen aufgerufen.
        """
        missing = []
        for name in self._tools:
            if name not in self._executors:
                missing.append(name)
        if missing:
            print(f"[Registry] ⚠️  Fehlende Executor für: {missing}")
        else:
            print(f"[Registry] ✅ Alle {len(self._tools)} Tools haben einen Executor.")


    @property
    def TOOLS(self) -> List[ToolDefinition]:
        """Dynamische Liste aller registrierten Tools (für Backward-Compatibility)."""
        return list(self._tools.values())


    # ====================== AUTOMATISCHES JSON-LOADING ======================
    def load_definitions_from_directory(self, directory: Path):
        """
        Lädt rekursiv alle Tool-Definitionen aus allen Unterordnern von definitions/.
        Unterstützt z. B. definitions/core/, definitions/web/, definitions/memory/ usw.
        """
        if not directory.exists():
            print(f"[Registry] Kein definitions-Ordner gefunden: {directory}")
            return


        # ============================================
        # Automatische Executor-Discovery (neu)
        # ============================================
        from backend.tools import loader

        # Rekursiv alle .json Dateien finden
        for json_file in sorted(directory.rglob("*.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                definition = ToolDefinition(**data)
                tool_name = definition.name

                executor = loader.get_executor(tool_name)

                if executor:
                    self.register(definition, executor)
                    print(f"[Registry] ✅ {tool_name} geladen aus {json_file.relative_to(directory)}")
                else:
                    self._tools[tool_name] = definition
                    print(f"[Registry] ⚠️  {tool_name} (nur Definition, kein Executor)")

            except Exception as e:
                print(f"[Registry] ❌ Fehler beim Laden von {json_file.name}: {e}")

        self.validate()
        try:
            from backend.tools import loader
            report = loader.get_integrity_report(set(self._tools.keys()))
            if report["healthy"]:
                print(f"[Registry] ✅ Integrity check passed — {report['total_registered_tools']} Tools / {report['total_discovered_executors']} Executors")
            else:
                print(f"[Registry] ⚠️  Integrity issues detected:")
                if report["missing_executors"]:
                    print(f"         Missing Executors for: {report['missing_executors']}")
                if report["missing_definitions"]:
                    print(f"         Executors without Definition: {report['missing_definitions']}")
        except Exception as e:
            print(f"[Registry] ⚠️  Integrity check failed: {e}")


# ====================== GLOBALE REGISTRY INSTANZ ======================
registry = ToolRegistry()
definitions_dir = Path(__file__).parent / "definitions"
registry.load_definitions_from_directory(definitions_dir)


# ====================== TOOL NAME NORMALIZATION + EXECUTION ======================
def normalize_tool_name(name: str) -> str:
    """Konvertiert camelCase / variationen in den exakten Tool-Namen."""
    import re
    name = name.strip().lower()
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name).lower()

    mapping = {
        "getcurrenttime": "get_current_time",
        "getserverinfo": "get_server_info",
        "getrandomnumber": "get_random_number",
        "reversetext": "reverse_text",
        "getweathermock": "get_weather_mock",
        "websearch": "web_search",
        "browseweb": "browse_page",
        "listpersonas": "list_personas",
        "resetpersona": "reset_persona",
        "setactivepersona": "set_active_persona",
        "getactivepersona": "get_active_persona",
        "clearactivepersona": "clear_active_persona",
        "listskills": "list_skills",
        "setactiveskill": "set_active_skill",
        "getactiveskill": "get_active_skill",
        "clearactiveskill": "clear_active_skill",
        "storememory": "store_memory",
        "recallmemory": "recall_memory",
        "listmemories": "list_memories",
        "clearmemory": "clear_memory",
        "clearchathistory": "clear_chat_history",
        "listchathistory": "list_chat_history",
        "addchatturn": "add_chat_turn",
        "fullreset": "full_reset",
        "getpromptstatus": "get_prompt_status",
    }
    return mapping.get(name, name)


def execute_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Führt ein Tool aus (mit Normalisierung + Fallback)."""
    name = normalize_tool_name(name)
    logger.info(f"🔧 [Fallback] Tool aufgerufen: {name}")

    try:
        result = registry.execute(name, args)
        return result
    except Exception as e:
        logger.error(f"💥 Fallback-Fehler bei Tool '{name}': {str(e)}")
        return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}


def refresh_default_session() -> int:
    """Erneuert die Default-Session (delegiert an memory.py)."""
    from ..memory import refresh_default_session as _refresh
    return _refresh()