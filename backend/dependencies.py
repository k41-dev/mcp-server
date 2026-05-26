#!/usr/bin/env python3
"""
dependencies.py - FastAPI Dependencies für Core Services

Ermöglicht saubere Dependency Injection von AgentContext, Registry und Settings.
"""

from fastapi import Depends
from typing import Annotated

from backend.config import settings
from backend.tools.context import AgentContext
from backend.tools.registry import registry as tool_registry


def get_settings():
    """Gibt die zentrale Settings-Instanz zurück."""
    return settings


def get_agent_context() -> AgentContext:
    """Gibt die aktuelle AgentContext-Instanz zurück (Singleton)."""
    return AgentContext.current()


def get_registry():
    """Gibt die globale Tool-Registry zurück."""
    return tool_registry


# Type Aliases für saubere Verwendung in FastAPI
SettingsDep = Annotated[object, Depends(get_settings)]
AgentContextDep = Annotated[AgentContext, Depends(get_agent_context)]
RegistryDep = Annotated[object, Depends(get_registry)]