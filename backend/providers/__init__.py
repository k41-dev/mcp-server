"""
backend/providers/__init__.py - Provider Registry + Auto-Registration
"""

from .base import ModelProvider, register_provider, get_provider, ToolCall

# Importiert die Provider → sie registrieren sich automatisch
from .xai import xai_provider
from .ollama import ollama_provider
from .openai import openai_provider
from .anthropic import anthropic_provider

__all__ = ["ModelProvider", "register_provider", "get_provider", "ToolCall"]