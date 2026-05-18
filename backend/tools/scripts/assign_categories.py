#!/usr/bin/env python3
"""
Einmal-Skript: Weist allen Tool-Definitionen sinnvolle Kategorien zu.
"""

import json
from pathlib import Path

DEFINITIONS_DIR = Path("backend/tools/definitions")

# === Hier das Mapping pflegen ===
CATEGORY_MAPPING = {
    # Core
    "get_current_time": "core",
    "echo": "core",
    "calculate": "core",
    "get_random_number": "core",
    "get_server_info": "core",
    "get_prompt_status": "core",
    "validate_tools": "core",
    "list_executors": "core",
    "reload_executors": "core",
    "get_current_context": "core",

    # Web
    "web_search": "web",
    "browse_page": "web",

    # Memory
    "store_memory": "memory",
    "recall_memory": "memory",
    "list_memories": "memory",
    "clear_memory": "memory",
    "add_chat_turn": "memory",
    "list_chat_history": "memory",
    "clear_chat_history": "memory",
    "full_reset": "memory",

    # Persona
    "list_personas": "persona",
    "set_active_persona": "persona",
    "get_active_persona": "persona",
    "clear_active_persona": "persona",
    "get_persona": "persona",

    # Skill
    "list_skills": "skill",
    "execute_skill": "skill",
    "set_active_skill": "skill",
    "get_active_skill": "skill",
    "clear_active_skill": "skill",
    "get_skill": "skill"
}

def assign_categories():
    updated = 0
    for json_file in DEFINITIONS_DIR.rglob("*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        tool_name = data.get("name")
        if not tool_name:
            continue

        category = CATEGORY_MAPPING.get(tool_name, "core")
        data["category"] = category

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ {tool_name} → {category}")
        updated += 1

    print(f"\nFertig. {updated} Tool-Definitionen aktualisiert.")


if __name__ == "__main__":
    assign_categories()