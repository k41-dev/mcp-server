"""
backend/providers/__init__.py - Provider Registry + Auto-Registration
"""

from .base import ModelProvider, register_provider, get_provider, ToolCall

# Importiert die Provider → sie registrieren sich automatisch
from .grok import grok_provider
from .ollama import ollama_provider

__all__ = ["ModelProvider", "register_provider", "get_provider", "ToolCall"]