#!/usr/bin/env python3
"""
core.py - Core Tools
"""

import datetime
import random
import ast
import operator
import json
import httpx
import logging
from typing import Dict, Any



SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


logger = logging.getLogger("mcp.tools")


def get_current_time(args: Dict[str, Any]) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": datetime.datetime.utcnow().isoformat() + "Z"}]}


def echo(args: Dict[str, Any]) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": args.get("message", "")}]}


def get_random_number(args: Dict[str, Any]) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": str(random.randint(args.get("min", 1), args.get("max", 100)))}]}


def safe_eval(expr: str) -> float:
    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp):
            return SAFE_OPERATORS[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return SAFE_OPERATORS[type(node.op)](_eval(node.operand))
        raise ValueError("Unsupported expression")
    try:
        return _eval(ast.parse(expr, mode='eval').body)
    except Exception as e:
        raise ValueError(str(e))


def calculate(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        result = safe_eval(args.get("expression", ""))
        return {"content": [{"type": "text", "text": str(result)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}


def get_server_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Returns basic server metadata and status including current AgentContext (pretty formatted)."""
    from backend.tools.registry import registry
    from backend.tools.context import AgentContext
    from backend.tools import loader
    import datetime

    try:
        ctx = AgentContext()
        tools_count = len(registry.get_all_definitions())

        # Prompt Version ermitteln
        prompt_version = "dynamic-v1"
        try:
            from backend.prompt_builder import get_prompt_version_only
            prompt_version = get_prompt_version_only(
                active_persona=ctx.active_persona,
                active_skill=ctx.active_skill,
                tools_count=tools_count,
                model=None
            )
        except Exception:
            pass

        # Kontext-Informationen
        persona = ctx.get_active_names()["persona"] or "None"
        skill = ctx.get_active_names()["skill"] or "None"
        summary = ctx.get_context_summary()

        executors_count = len(loader.get_all_executors())

        # === Neue Integrity-Prüfung ===
        integrity = loader.get_integrity_report(
            set(t.name for t in registry.get_all_definitions())
        )
        integrity_status = "✅ healthy" if integrity["healthy"] else "⚠️ issues found"

        # === Tools nach Kategorie gruppieren ===
        from collections import defaultdict
        tools_by_category: dict[str, list[str]] = defaultdict(list)

        for tool in registry.get_all_definitions():
            cat = getattr(tool, "category", "core") or "core"
            tools_by_category[cat].append(tool.name)

        # Schöne Kategorien-Übersicht bauen
        category_lines = []
        for category in sorted(tools_by_category.keys()):
            names = ", ".join(sorted(tools_by_category[category]))
            category_lines.append(f"• {category}: {names} ({len(tools_by_category[category])})")

        tools_overview = "\n".join(category_lines)

        # Schöne Text-Ausgabe
        output = f"""Status: running

* Version: 1.0.0
* Tools Loaded: {tools_count}
* Executors Discovered: {executors_count}
* Integrity: {integrity_status}
* Prompt Version: {prompt_version}
* Timestamp: {datetime.datetime.utcnow().isoformat() + "Z"}
* Context: active_persona = "{persona}", active_skill = "{skill}", context_summary = "{summary}"

**Tools by Category:**
{tools_overview}
"""

        return {
            "content": [{
                "type": "text",
                "text": output
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error in get_server_info: {str(e)}"
            }],
            "isError": True
        }


def get_prompt_status(args: Dict[str, Any]) -> Dict[str, Any]:
    """Returns current prompt version + active persona/skill/model.
    
    Berücksichtigt jetzt auch das aktive Modell aus dem Kontext.
    """
    import json
    import datetime
    from backend.tools.context import AgentContext
    from backend.tools.registry import registry

    try:
        ctx = AgentContext()
        tools_count = len(registry.get_all_definitions())

        # Version berechnen (jetzt mit aktivem Model)
        version = "dynamic-v1"
        try:
            from backend.prompt_builder import get_prompt_version_only
            version = get_prompt_version_only(
                active_persona=ctx.active_persona,
                active_skill=ctx.active_skill,
                tools_count=tools_count,
                model=ctx.active_model          # ← wichtig
            )
        except Exception:
            names = ctx.get_active_names()
            key = f"{names['model'] or 'none'}|{names['persona'] or 'none'}|{names['skill'] or 'none'}|{tools_count}"
            version = f"dynamic-{hash(key) % 100000}"

        # Basis-Status + aktives Model
        status = ctx.to_dict()
        status.update({
            "version": version,
            "tools_loaded": tools_count,
            "computed_at": datetime.datetime.utcnow().isoformat() + "Z",
            "note": "Skill injection is active" if ctx.has_active_skill else None
        })

        return {
            "content": [{
                "type": "text",
                "text": json.dumps(status, indent=2)
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error in get_prompt_status: {str(e)}"
            }],
            "isError": True
        }


def get_current_context(args: Dict[str, Any]) -> Dict[str, Any]:
    """Returns the full current AgentContext with additional metadata.
    
    Berücksichtigt jetzt auch das aktive Modell.
    """
    from backend.tools.context import AgentContext
    from backend.tools.registry import registry
    import json
    import datetime

    try:
        ctx = AgentContext()
        tools_count = len(registry.get_all_definitions())

        # Prompt-Version ermitteln (mit aktivem Model)
        version = "dynamic-v1"
        try:
            from backend.prompt_builder import get_prompt_version_only
            version = get_prompt_version_only(
                active_persona=ctx.active_persona,
                active_skill=ctx.active_skill,
                tools_count=tools_count,
                model=ctx.active_model          # ← wichtig
            )
        except Exception:
            pass

        # Reichen Kontext aufbauen
        context_data = ctx.to_dict()
        context_data.update({
            "prompt_version": version,
            "tools_loaded": tools_count,
            "computed_at": datetime.datetime.utcnow().isoformat() + "Z",
            "summary": ctx.get_context_summary()
        })

        return {
            "content": [{
                "type": "text",
                "text": json.dumps(context_data, indent=2, ensure_ascii=False)
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error getting current context: {str(e)}"
            }],
            "isError": True
        }


def list_executors(args: Dict[str, Any]) -> Dict[str, Any]:
    """Gibt alle dynamisch entdeckten Executor-Funktionen zurück."""
    from backend.tools import loader

    executors = loader.get_all_executors()
    if not executors:
        return {
            "content": [{"type": "text", "text": "No executors discovered."}]
        }

    names = sorted(executors.keys())
    text = f"**Discovered Executors ({len(names)}):**\n\n"
    text += "\n".join([f"• {name}" for name in names])

    return {
        "content": [{"type": "text", "text": text}]
    }


def reload_executors(args: Dict[str, Any]) -> Dict[str, Any]:
    """Erzwingt ein erneutes Scannen aller Executor-Module (ohne Container-Restart)."""
    from backend.tools import loader

    count_before = len(loader.get_all_executors())
    new_count = loader.reload_executors()

    return {
        "content": [{
            "type": "text",
            "text": f"✅ Executors reloaded.\nBefore: {count_before} → After: {new_count}"
        }]
    }


def validate_tools(args: Dict[str, Any]) -> Dict[str, Any]:
    """Prüft die Konsistenz zwischen Tool-Definitionen und Executor-Funktionen.
    
    Gibt einen detaillierten Report zurück (missing executors, missing definitions etc.).
    Sehr nützlich für Debugging nach Strukturänderungen.
    """
    import json
    from backend.tools import loader, registry as _registry

    try:
        registered_names = set(t.name for t in _registry.get_all_definitions())
        report = loader.get_integrity_report(registered_names)

        output = json.dumps(report, indent=2, ensure_ascii=False)

        return {
            "content": [{
                "type": "text",
                "text": f"**Tool Integrity Report**\n\n{output}"
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error in validate_tools: {str(e)}"
            }],
            "isError": True
        }


def list_tools_by_category(args: Dict[str, Any]) -> Dict[str, Any]:
    """Listet alle Tools gruppiert nach Kategorie auf.
    
    Optional kann eine bestimmte Kategorie über den Parameter 'category' gefiltert werden.
    """
    from backend.tools.registry import registry
    from collections import defaultdict
    import json

    requested_category = args.get("category", "").strip().lower()

    tools_by_category: dict[str, list[str]] = defaultdict(list)

    for tool in registry.get_all_definitions():
        cat = getattr(tool, "category", "core") or "core"
        tools_by_category[cat].append(tool.name)

    if requested_category:
        if requested_category not in tools_by_category:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Keine Tools für Kategorie '{requested_category}' gefunden."
                }]
            }
        names = ", ".join(sorted(tools_by_category[requested_category]))
        text = f"**{requested_category.upper()}** ({len(tools_by_category[requested_category])} Tools):\n{names}"
    else:
        # Alle Kategorien anzeigen
        lines = []
        for category in sorted(tools_by_category.keys()):
            names = ", ".join(sorted(tools_by_category[category]))
            lines.append(f"**{category}** ({len(tools_by_category[category])}): {names}")
        text = "\n\n".join(lines)

    return {
        "content": [{
            "type": "text",
            "text": text
        }]
    }


def set_active_provider(args: Dict[str, Any]) -> Dict[str, Any]:
    """Setzt den aktiven Provider (xai, ollama, openai oder anthropic)."""
    from backend.tools.state import set_active_provider as _set_active_provider

    # Unterstützt beide möglichen Keys (alter + neuer Name)
    provider_name = args.get("provider") or args.get("model")
    provider_name = str(provider_name).strip().lower()

    if not provider_name:
        return {
            "content": [{"type": "text", "text": "Error: 'provider' (oder 'model') Parameter fehlt"}],
            "isError": True
        }

    if provider_name not in ("xai", "ollama", "openai", "anthropic"):
        return {
            "content": [{"type": "text", "text": f"Error: Ungültiger Provider '{provider_name}'"}],
            "isError": True
        }

    _set_active_provider(provider_name)
    return {
        "content": [{"type": "text", "text": f"✅ Active provider set to: {provider_name}"}]
    }


def get_active_provider(args: Dict[str, Any]) -> Dict[str, Any]:
    """Gibt den aktuell aktiven Provider zurück."""
    from backend.tools.state import get_active_provider as _get_active_provider
    import json

    try:
        provider = _get_active_provider()
        if provider:
            return {
                "content": [{"type": "text", "text": json.dumps({"active_provider": provider})}]
            }
        else:
            return {
                "content": [{"type": "text", "text": "No active provider set (using default Grok)."}]
            }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error getting active provider: {str(e)}"}],
            "isError": True
        }


def clear_active_provider(args: Dict[str, Any]) -> Dict[str, Any]:
    """Entfernt den aktuell aktiven Provider aus dem Kontext."""
    from backend.tools.state import clear_active_provider as _clear_active_provider

    _clear_active_provider()
    return {
        "content": [{"type": "text", "text": "✅ Active provider cleared. System will fall back to default (Grok)."}]
    }


def get_active_model(args: Dict[str, Any]) -> Dict[str, Any]:
    """Gibt das aktuell aktive Modell (konkreter Name aus Settings) zurück."""
    from backend.tools.state import get_active_model as _get_active_model
    import json

    try:
        model = _get_active_model()
        if model:
            return {
                "content": [{"type": "text", "text": json.dumps({"active_model": model})}]
            }
        else:
            return {
                "content": [{"type": "text", "text": "No active model resolved."}]
            }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error getting active model: {str(e)}"}],
            "isError": True
        }