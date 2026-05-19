#!/usr/bin/env python3
"""
config.py - Zentrale, immutable Konfigurationsabstraktion

Single Source of Truth für alle Umgebungsvariablen im Backend.
Ermöglicht Typsicherheit, Defaults und einfaches Mocking in Tests.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Settings:
    """Immutable Settings — wird einmal beim Import erzeugt."""

    # === xAI / Grok ===
    XAI_API_KEY: str = os.getenv("XAI_API_KEY", "")
    XAI_MODEL: str = os.getenv("XAI_MODEL", "grok-4.3")

    # === Ollama ===
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
    OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    # === MCP Server ===
    MCP_PUBLIC_URL: str = os.getenv("MCP_PUBLIC_URL", "http://localhost:8321")
    MCP_API_KEY: str = os.getenv("MCP_API_KEY", "")

    # === Prompt-Dateien ===
    SYSTEM_PROMPT_GROK: str = os.getenv("SYSTEM_PROMPT_GROK", "system_prompt_grok.md")
    SYSTEM_PROMPT_OLLAMA: str = os.getenv("SYSTEM_PROMPT_OLLAMA", "system_prompt_ollama.md")

    # === Web Tools ===
    SEARXNG_URL: str = os.getenv("SEARXNG_URL", "http://searxng:8080")
    BROWSERLESS_URL: str = os.getenv("BROWSERLESS_URL", "http://browserless:3000")
    BROWSERLESS_TOKEN: str = os.getenv("BROWSERLESS_TOKEN", "")

    # === Optional / Zukunft ===
    PORT: int = int(os.getenv("PORT", "8321"))

    @property
    def has_xai_key(self) -> bool:
        return bool(self.XAI_API_KEY.strip())

    @property
    def is_production(self) -> bool:
        return bool(self.MCP_API_KEY) and self.MCP_API_KEY != "your_mcp_authtoken_here"


# Globale, immutable Instanz (wird beim ersten Import erzeugt)
settings = Settings()