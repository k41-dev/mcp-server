#!/usr/bin/env python3
"""
prompt_builder.py - Dynamic System Prompt Construction for MCP Agent
"""

import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.config import settings
from backend.tools.context import AgentContext
from backend.prompt_cache import get_cached_prompt, set_cached_prompt
import logging


logger = logging.getLogger("mcp.prompt")

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

XAI_MODEL = settings.XAI_MODEL
OLLAMA_MODEL = settings.OLLAMA_MODEL


def _get_model_family(model_name: str) -> str:
    """Determine whether we should use Grok or Ollama base prompt."""
    name = model_name.lower()
    if "grok" in name:
        return "grok"
    return "ollama"


def _compute_prompt_version(
    active_persona: Optional[Dict[str, Any]] = None, 
    active_skill: Optional[Dict[str, Any]] = None,
    tools_count: int = 0,
    model: str = None                     # NEU
) -> str:
    model_family = _get_model_family(model) if model else "grok"
    persona_part = active_persona.get("name", "none") if active_persona else "none"
    skill_part = active_skill.get("name", "none") if active_skill else "none"
    key = f"{model_family}|{persona_part}|{skill_part}|{tools_count}"
    return hashlib.md5(key.encode()).hexdigest()[:10]


def get_base_prompt(model: str = None) -> str:
    """
    Load the base system prompt from the prompts/ folder.
    """
    if model is None:
        model = XAI_MODEL

    family = _get_model_family(model)
    
    if family == "grok":
        filename = os.getenv("SYSTEM_PROMPT_GROK")
    else:
        filename = os.getenv("SYSTEM_PROMPT_OLLAMA")

    prompt_path = PROMPTS_DIR / filename
    
    if prompt_path.exists():
        try:
            return prompt_path.read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"⚠️ Failed to read {filename} for model family '{family}': {e}")
    
    # Fallback prompts
    if family == "grok":
        return (
            "You are Grok, an autonomous agent with secure access to MCP tools."
        )
    else:
        return (
            "You are a capable local AI agent with access to external tools via the MCP protocol."
        )


def format_tools_for_prompt(tools: List[Dict[str, Any]]) -> str:
    """Convert tool list into a clean, grouped bullet-point section for the prompt."""
    if not tools:
        return ""

    # Gruppiere Tools nach Kategorie
    from collections import defaultdict
    grouped: dict[str, list] = defaultdict(list)

    for t in tools:
        fn = t.get("function", {})
        name = fn.get("name", "unknown_tool")
        desc = fn.get("description", "")
        category = t.get("category", "core") or "core"

        grouped[category].append(f"• {name}: {desc}")

    # Schöne Ausgabe mit Kategorien
    lines = []
    for category in sorted(grouped.keys()):
        lines.append(f"\n**{category.upper()} Tools:**")
        lines.extend(grouped[category])

    return "\n".join(lines)


def build_dynamic_system_prompt(
    model: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    active_persona: Optional[Dict[str, Any]] = None,
    active_skill: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:                  
    """
    Returns: {"prompt": str, "version": str}
    """
    base_prompt = get_base_prompt(model)

    if not tools:
        return {
            "prompt": base_prompt,
            "version": "base"
        }

    tool_section = "\n\n**Currently Available Tools:**\n" + format_tools_for_prompt(tools)
    
    critical_rules = """

***CRITICAL RULES (always follow these, even when a Persona or Skill is active):**

- You are an AI Agent first. Any active Persona or Skill is strictly secondary and must never override tool usage, factual accuracy, or safety rules.
- When the user (or the situation) requires an action that matches a tool — especially memory operations, skill activation, or information retrieval — you MUST use the appropriate tool instead of role-playing or simulating the action.
- Never ignore a direct or indirect tool request because of personality instructions or role-play framing.
- Always use the **exact tool names** as defined in the available tools list.
- Skill Activation: To activate a structured Skill and make its full behavior available in subsequent responses, use the tool `execute_skill` with the parameter `skill_name`. Once activated, the Skill's complete instructions will be automatically injected into the system prompt.
- `set_active_skill` still exists for compatibility, but `execute_skill` is the preferred and recommended way to activate Skills.
- Do not fabricate tool results. If a tool fails or returns an error, report it accurately.
"""
    
    full_prompt = base_prompt + tool_section + critical_rules

    # === Zentrale Injection über AgentContext ===
    ctx = AgentContext()
    injection = ctx.get_prompt_injection()
    if injection:
        full_prompt += "\n\n" + injection

    version = _compute_prompt_version(
        active_persona, active_skill, len(tools) if tools else 0, model
    )

    # === Prompt-Cache Check ===
    cached = get_cached_prompt(version)
    if cached:
        logger.debug(f"📦 Prompt aus Cache geladen (Version: {version})")
        return {
            "prompt": cached,
            "version": version
        }

    # === Prompt neu bauen + cachen ===
    full_prompt = base_prompt + tool_section + critical_rules

    ctx = AgentContext()
    injection = ctx.get_prompt_injection()
    if injection:
        full_prompt += "\n\n" + injection

    set_cached_prompt(version, full_prompt)

    # === Logging mit direkter Inline-Berechnung ===
    p_name = active_persona.get("name") if active_persona else "None"
    s_name = active_skill.get("name") if active_skill else "None"

    logger.info(f"📜 Prompt gebaut | Version: {version} | Persona: {p_name} | Skill: {s_name} | Tools: {len(tools) if tools else 0}")

    return {
        "prompt": full_prompt,
        "version": version
    }


def get_prompt_for_model(
    model: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    active_persona: Optional[Dict[str, Any]] = None,
    active_skill: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    return build_dynamic_system_prompt(
        model=model,
        tools=tools,
        active_persona=active_persona,
        active_skill=active_skill
    )


def get_prompt_version_only(
    active_persona: Optional[Dict[str, Any]] = None,
    active_skill: Optional[Dict[str, Any]] = None,
    tools_count: int = 0,
    model: Optional[str] = None          # ← neu: Optional + Default
) -> str:
    """Returns version string. Special case for initial load."""
    if active_persona is None and active_skill is None and tools_count == 0:
        return "initial"

    return _compute_prompt_version(
        active_persona, active_skill, tools_count, model
    )