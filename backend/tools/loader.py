#!/usr/bin/env python3
"""
loader.py - Automatische Tool-Executor Discovery

Single Source of Truth für die dynamische Entdeckung aller Executor-Funktionen.
Ermöglicht es, neue Tools hinzuzufügen, ohne registry.py oder andere Dateien
zu verändern (außer der neuen Executor-Datei + JSON-Definition).

Design-Prinzipien:
- Zero-Config: Neue .py-Datei in executors/ → wird automatisch erkannt
- Defensive: Import-Fehler einzelner Module brechen das System nicht
- Logging-fähig für Debugging
"""

import importlib
import pkgutil
from typing import Dict, Callable, Any, Optional
import logging

logger = logging.getLogger("mcp.loader")

EXECUTORS_PACKAGE = "backend.tools.executors"


def discover_executors() -> Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]]:
    """
    Entdeckt alle Python-Module unter backend/tools/executors/ automatisch
    und extrahiert nur echte Tool-Executor-Funktionen.
    """
    import inspect
    executors: Dict[str, Callable] = {}

    try:
        package = importlib.import_module(EXECUTORS_PACKAGE)
    except ImportError as e:
        logger.error(f"❌ Konnte Executors-Package nicht importieren: {e}")
        return executors

    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
        if ispkg:
            continue

        try:
            module = importlib.import_module(f"{EXECUTORS_PACKAGE}.{modname}")

            for attr_name in dir(module):
                if attr_name.startswith("_"):
                    continue

                attr = getattr(module, attr_name)
                if not callable(attr):
                    continue

                if getattr(attr, "__module__", None) != module.__name__:
                    continue

                try:
                    sig = inspect.signature(attr)
                    if len(sig.parameters) != 1:
                        continue
                    if attr_name in {"safe_eval"}:
                        continue

                except (ValueError, TypeError):
                    continue

                executors[attr_name] = attr
                logger.debug(f"✓ Executor entdeckt: {attr_name} (aus {modname}.py)")

        except Exception as e:
            logger.warning(f"⚠️  Modul {modname}.py konnte nicht geladen werden: {e}")

    logger.info(f"✅ {len(executors)} echte Tool-Executor-Funktionen automatisch entdeckt")
    return executors


# ============================================
# Globale Instanz (wird beim Import einmal ausgeführt)
# ============================================
_discovered_executors: Dict[str, Callable] = discover_executors()


def get_executor(tool_name: str) -> Optional[Callable]:
    """Gibt die passende Executor-Funktion für einen Tool-Namen zurück."""
    return _discovered_executors.get(tool_name)


def get_all_executors() -> Dict[str, Callable]:
    """Gibt eine Kopie der aktuell entdeckten Executor-Map zurück (für Debugging)."""
    return _discovered_executors.copy()


def reload_executors() -> int:
    """
    Erzwingt ein erneutes Scannen der Executor-Module.
    Nützlich während der Entwicklung.
    """
    global _discovered_executors
    _discovered_executors = discover_executors()
    return len(_discovered_executors)


def get_integrity_report(registered_tool_names: set[str]) -> dict:
    """
    Vergleicht die automatisch entdeckten Executor-Funktionen mit den
    registrierten Tool-Definitionen aus der Registry.
    """
    discovered = set(_discovered_executors.keys())
    registered = registered_tool_names or set()

    missing_executors = sorted(registered - discovered)
    missing_definitions = sorted(discovered - registered)
    healthy = len(missing_executors) == 0 and len(missing_definitions) == 0

    if not healthy:
        logger.warning(f"Tool Integrity issues: {len(missing_executors)} missing executors, {len(missing_definitions)} missing definitions")

    return {
        "status": "healthy" if healthy else "issues_found",
        "healthy": healthy,
        "total_discovered_executors": len(discovered),
        "total_registered_tools": len(registered),
        "missing_executors": missing_executors,
        "missing_definitions": missing_definitions,
        "checked_at": __import__("datetime").datetime.utcnow().isoformat() + "Z"
    }