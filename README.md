# Wäärkzüüg-Chaschte 🧰

## Prerequisites

Before starting the MCP Agent Platform, make sure the following tools are installed:

### 1. uv (recommended Python package manager)

`uv` is used for fast dependency management and running Python scripts in this project.

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
Alternative installation via pip:

pip install uv

2. Docker & Docker Compose
Install Docker Desktop (recommended for most users) or Docker Engine + Docker Compose plugin.
Verify your installation:

docker --version
docker compose version

3. Create the required Docker network
The project uses an external Docker network named app-net for inter-container communication with static IPs. This network must be created manually before the first startup:
docker network create app-net

Verify it was created:
docker network ls | grep app-net

Once these steps are complete, you can start the project with:
docker compose up --build -d



**Production-grade autonomous agent server** with JSON-RPC MCP endpoint, persistent vector memory, dynamic persona/skill injection, and dual-model support (Grok + Ollama).

Built and maintained under strict architectural discipline for long-term stability, zero-surprise deployments, and clean separation of concerns.

**Version:** 1.0.0  
**Date:** 2026-05-18  
**Status:** Stable foundational release

---

## Executive Summary

This platform provides a complete, containerized environment for running a tool-calling AI agent:

- **MCP Server** (`backend/server.py`): FastAPI-based JSON-RPC 2.0 endpoint (`/mcp`) implementing a custom MCP protocol.
- **32 Tools**: Core utilities, web search/browse (SearXNG + Browserless), persistent memory, persona management, skill activation, and utility tools — all auto-discovered from a clean category-based folder structure.
- **Dynamic System Prompts**: `prompt_builder.py` composes versioned prompts on-the-fly (MD5 hash of persona + skill + tool count), injecting current tools + active persona + active skill (skills have strict priority).
- **Persistent Memory**: Hybrid SQLite + `sqlite-vec` + Ollama `nomic-embed-text` embeddings for semantic long-term recall.
- **Gradio UI** (`frontend/gradio_app.py`): Full-featured chat interface with live controls — **never imports backend code**. Pure dumb client over MCP.
- **CLI Client** (`client.py`): Scriptable full multi-turn agent loops for Grok and Ollama with memory integration and streaming.
- **Docker Compose**: Three services (`mcp-server`, `agent-ui`, `ngrok`) with healthchecks, volumes for prompts/data, and clean networking.

The architecture was hardened through multiple iterations. The guiding principle is **long-term maintainability and architectural purity > clever hacks**.

---

## Project Structure (Complete Overview)

```
MCP Agent Platform v1.0.0
├── backend/                          # Core server & business logic (Single Source of Truth)
│   ├── server.py                     # FastAPI JSON-RPC handler (/mcp endpoint)
│   ├── prompt_builder.py             # Dynamic system prompt engine + versioning
│   ├── memory.py                     # SQLite + sqlite-vec long-term memory
│   ├── tools/
│   │   ├── registry.py               # Tool factory & auto-loader (rglob *.json)
│   │   ├── loader.py                 # Automatic executor discovery + integrity checks
│   │   ├── context.py                # AgentContext – single source for persona/skill
│   │   ├── state.py                  # Centralized active persona/skill storage
│   │   ├── definitions/              # All 32 tool JSON definitions (category-based)
│   │   │   ├── core/                 # 11 foundational tools
│   │   │   ├── memory/               # 8 memory tools
│   │   │   ├── persona/              # 5 persona tools
│   │   │   ├── skill/                # 6 skill tools
│   │   │   ├── web/                  # 2 web tools
│   │   ├── executors/                # Python implementations (auto-discovered)
│   │   │   ├── core.py
│   │   │   ├── memory.py
│   │   │   ├── persona.py
│   │   │   ├── skill.py
│   │   │   └── web.py
│   │   ├── repositories/             # Persona & Skill content loaders
│   │   │   ├── persona_repository.py
│   │   │   └── skill_repository.py
│   │   └── __init__.py
│   ├── scripts/
│   │   └── assign_categories.py      # One-time category assignment helper
│   └── __init__.py
├── frontend/                         # Pure UI layer (never imports backend/)
│   ├── gradio_app.py                 # Full Gradio 6 web interface
│   ├── client.py                     # CLI agent (Grok + Ollama loops)
│   └── style.css                     # Custom dark theme
├── prompts/                          # All persona & skill content
│   ├── personas/
│   │   ├── professor.md
│   │   ├── comedian.md
│   │   ├── pirate.md
│   │   └── detective.md
│   └── skills/
│       └── comic_glitch_creator.md   # Full ReAct + CoT skill
├── docker-compose.yml                # 3 services (mcp-server, agent-ui, ngrok)
├── Dockerfile                        # mcp-server image
├── Dockerfile.ui                     # agent-ui image
├── pyproject.toml
├── requirements.txt
├── env.example.txt
└── README.md                         # This file (single source of truth)
```

**Key Principles visible in the structure:**
- `backend/` = Server, Tools, Memory, Prompt Logic
- `frontend/` = Reine UI (kommuniziert **ausschließlich** über `/mcp`)
- `prompts/` = Personas & Skills (höhere Priorität für Skills)
- Alles auto-discovered → keine manuellen Registrierungen

---

## Architecture (Holy Rules — Non-Negotiable)

### Strict Layering
```
backend/          → Server, Tools (registry + executors), Memory, Prompt Logic, Business Rules, State
frontend/         → Pure UI layer (Gradio 6). **MUST NOT** import anything from backend/
```

- All UI ↔ Backend communication happens **exclusively** over the MCP JSON-RPC endpoint (`POST /mcp`).
- `prompt_builder.py` is the **Single Source of Truth** for all system prompts.
- `backend/tools/registry.py` + JSON definitions in `backend/tools/definitions/` (core/, memory/, persona/, skill/, web/, utility/) are the Single Source of Truth for tools.
- Docker Compose + `.env` is the source of truth for runtime. Local edits without rebuild are meaningless.
- `__pycache__` must be deleted in both containers after any structural Python change.

### Tool Definitions Folder Structure (for the 32 Tools)

```
backend/tools/definitions/
├── core/                     # Foundational tools (~11)
├── memory/                   # 8 tools
├── persona/                  # 5 tools
├── skill/                    # 6 tools
├── web/                      # 2 tools
└── utility/                  # NEW category for additional tools
```

**Rules:**
- Every tool = exactly one `.json` file with `name`, `description`, `inputSchema`, optional `category`.
- Executor must exist in `backend/tools/executors/<name>.py` (auto-discovered by `loader.py`).
- New category? Create folder + (optional) entry in `assign_categories.py`.
- After changes: Use `validate_tools` or `reload_executors` via MCP.

### Critical Design Decisions
- **Tool Calling**: Grok uses native OpenAI-compatible `tools` + `tool_choice="auto"`. Ollama uses native tools + defensive raw-JSON fallback parser. **Never touch Grok path when fixing Ollama.**
- **Persona/Skill Injection**: Skills > Personas. Both injected via `AgentContext`. Core agent rules (tool usage, truth, safety) **always** override personality instructions.
- **Memory**: Chat history + long-term semantic facts (vector search). `add_chat_turn` automatically called.
- **Auto-Discovery**: Tools (JSON + executors), Personas (`prompts/personas/*.md`), Skills (`prompts/skills/*.md`) — zero-config.
- **Versioning**: Stable MD5 version for every dynamic prompt.

---

## Complete Feature List (v1.0.0)

### 1. Dual-Model Agent System
- **Grok Path** (xAI Grok-4.3): Native tool calling, up to 6 turns, automatic tool result injection, context line (`🎭 Persona • 🛠️ Skill`).
- **Ollama Path** (e.g. llama3.1:latest): Native tools + robust JSON fallback parser. MAX_TURNS=4. Full streaming support.
- Dynamic model switch instantly refreshes system prompt.

### 2. Dynamic System Prompt Engine (`prompt_builder.py`)
- Loads base prompt from `prompts/system_prompt_grok.md` or `prompts/system_prompt_ollama.md`.
- Injects **formatted tool list** grouped by category.
- Appends **CRITICAL RULES** (tool priority, no hallucination, exact tool names, `execute_skill` preferred).
- Injects active **Skill** (highest priority) + **Persona**.
- Computes stable version hash: `persona|skill|tool_count`.
- `prompts/get_dynamic` returns `{"prompt": "...", "version": "abc123def0"}`.

### 3. 32 Tools (Auto-Loaded & Categorized)
All tools defined in `backend/tools/definitions/{category}/*.json` + executors in `backend/tools/executors/*.py` (auto-discovered by `loader.py`).

**Core (11)**
- `get_current_time`, `echo`, `calculate` (safe AST eval), `get_random_number`, `get_server_info` (full status + integrity + tools_by_category), `get_prompt_status`, `get_current_context`, `list_executors`, `reload_executors`, `validate_tools`

**Web (2)**
- `web_search` (SearXNG), `browse_page` (Browserless or direct BeautifulSoup with cleanup)

**Memory (8)**
- `store_memory`, `recall_memory` (vector + text fallback), `list_memories`, `clear_memory`
- `add_chat_turn`, `list_chat_history`, `clear_chat_history`, `full_reset` (nuclear DB wipe)

**Persona (5)**
- `list_personas`, `set_active_persona`, `get_active_persona`, `clear_active_persona`, `get_persona` (raw content)

**Skill (6)**
- `list_skills`, `execute_skill` (preferred activation — loads full content), `set_active_skill`, `get_active_skill`, `clear_active_skill`, `get_skill` (raw content)

**Integrity & Debugging**
- `validate_tools` returns detailed report (missing executors, missing definitions).
- `reload_executors` hot-reloads without container restart.
- `get_server_info` shows live integrity status, prompt version, tools_by_category.

### 4. Persona System (4 built-in)
Located in `prompts/personas/`:
- `professor.md` — Patient, precise, elegant academic (Professor Elias Thornwood)
- `comedian.md` — Sarcastic, chaotic stand-up (Rusty Quill)
- `pirate.md` — Theatrical Captain Silas Blackwake
- `detective.md` — Calm, precise Inspector Margot Vale

Activation via `set_active_persona` (intensity 1-10) or UI dropdown. Fully injected into every prompt.

### 5. Skill System (Higher Priority than Personas)
Located in `prompts/skills/`:
- `comic_glitch_creator.md` — Full **ReAct + Chain-of-Thought** workflow for generating exactly 10 unique 75-100 word comic prompts (Bill Sienkiewicz chaotic style + GlitchArt + neon + filters). Strict output format, research loop, reflection phase.

Activation: **Use `execute_skill` tool** (recommended). Once active, full skill content is injected and takes precedence.

### 6. Gradio Web UI (frontend/gradio_app.py)
- **Status bar** with live tool count + model selector (Grok / Ollama)
- **Full-height Chat** with avatars, tool-step indicators, context line
- **📜 System Prompt Accordion** — live viewer + refresh (exact injected prompt + version)
- **🎭 Persona Control** — dropdown, intensity slider (1-10), Apply/Reset
- **🛠️ Skill Control** — dropdown, Activate (uses `execute_skill`), Reset
- **🛠️ Available Tools Accordion** — categorized dropdown + description + "➕ Insert Tool"
- **🧠 Memory Panel** — Show/Clear LT-Memory, Show/Clear Chat History, Full Nuclear Reset
- All actions call MCP tools and auto-refresh dynamic prompt.
- Responsive, custom dark theme (`style.css`).

### 7. CLI Agent (client.py)
- `uv run client.py grok "query"` — full tool-calling loop + memory context + optional `--stream`
- `uv run client.py ollama "query" [--model ...] [--stream]`
- `uv run client.py mcp-list` / `mcp-call tool_name --args '{...}'`
- Automatically loads recent chat history + relevant long-term memories.
- Saves every turn via `add_chat_turn`.

### 8. Persistent Memory Layer (backend/memory.py)
- SQLite + `sqlite-vec` (768-dim nomic-embed-text embeddings).
- Sessions, chat messages, long-term facts.
- Semantic recall (vector search with LIKE fallback).
- `full_reset()` nukes entire DB and recreates clean tables.
- Auto-initialized. `DEFAULT_SESSION_ID` managed centrally.

### 9. State Management (`backend/tools/state.py` + `context.py`)
- Centralized `_active_persona` / `_active_skill` (per DEFAULT_SESSION_ID).
- `AgentContext` class: single source of truth for prompt injection and active names.
- All persona/skill tools delegate to state manager.

### 10. Docker & Deployment
- `mcp-server` (8321): FastAPI + uvicorn, healthcheck, volumes for data/ + prompts/
- `agent-ui` (7860): Gradio, depends on mcp-server
- `ngrok` (optional): Public HTTPS with custom domain
- Networks: `app-net` (static IPs)
- After changes: `docker compose build && docker compose up -d` + `__pycache__` cleanup in both containers.

### 11. Configuration (.env)
- `XAI_API_KEY`, `XAI_MODEL=grok-4.3`
- `OLLAMA_URL` (auto-detected), `OLLAMA_MODEL`, `OLLAMA_EMBED_MODEL`
- `MCP_PUBLIC_URL`, `NGROK_*`
- `SYSTEM_PROMPT_GROK` / `SYSTEM_PROMPT_OLLAMA`
- `SEARXNG_URL`, `BROWSERLESS_URL` / `BROWSERLESS_TOKEN`

### 12. Developer Experience & Debugging
- `assign_categories.py` — one-time category tagging script.
- `loader.py` — automatic executor discovery + integrity report.
- `validate_tools` MCP tool for post-change verification.
- Strict rules enforced everywhere.
- All errors return structured `{"content": [...], "isError": true}`.

---

## Quick Start (Docker — Recommended)

```bash
cp env.example.txt .env
# Edit .env — minimum: XAI_API_KEY + OLLAMA_MODEL + (optional) NGROK_*

docker compose up --build -d

# Access
# Gradio UI:  http://localhost:7860
# MCP:        http://localhost:8321/mcp  (or your ngrok URL)
# Health:     curl http://localhost:8321/
```

**After any backend change**:
```bash
docker compose build mcp-server && docker compose up -d mcp-server
docker compose exec mcp-server find /app -type d -name __pycache__ -exec rm -rf {} +
```

**After any frontend change**:
```bash
docker compose build agent-ui && docker compose up -d agent-ui
docker compose exec agent-ui find /app -type d -name __pycache__ -exec rm -rf {} +
```

---

## Development Guidelines (MCP Projektleiter Doctrine)

1. **Never** import from `backend/` inside `gradio_app.py` or any frontend file.
2. **Always** ask: "Does this require a container rebuild?"
3. Prefer **small, targeted edits** over large replacements.
4. Ollama fixes → only in the `else` (Ollama) block. Never touch Grok path.
5. After structural changes → delete `__pycache__` in **both** containers.
6. When in doubt: restore known-good state first, then iterate.
7. New tools: add JSON in `definitions/{category}/` + executor in `executors/`. Zero other changes needed.
8. New Persona/Skill: drop `.md` file in `prompts/{personas,skills}/`. Auto-discovered.

---

## Current Tool Integrity (v1.0.0)

All 32 tools have matching executors. Registry + loader perform automatic validation on startup. `get_server_info` and `validate_tools` provide live reports.

---

## Why v1.0.0 Exists

This release establishes the clean, disciplined foundation after multiple painful restructurings. It eliminates:
- UI importing backend logic
- Fragile Ollama handling
- Unversioned prompts
- Manual tool registration

Everything is now auto-discovered, centrally versioned, and strictly layered under a scalable folder structure.

---

## Recent Improvements (May 2026)

Since the initial v1.0.0 release, the following stability and maintainability improvements have been implemented:

- **Structured Tool Lists** — `list_personas` and `list_skills` now return clean JSON arrays instead of formatted text. The Gradio UI parses this directly (with fallback for compatibility).
- **Startup Integrity Gate** — Automatic tool integrity check on server startup with clear logging and warnings for missing executors or definitions.
- **Enhanced Health Endpoint** — `/health` now returns detailed status including active persona, active skill, tool integrity, and executor discovery state.
- **Improved Logging** — `loader.py` migrated from `print()` to structured `logging` with consistent levels and better debug output.
- **UI Cleanup** — Tool insertion logic in `gradio_app.py` consolidated and simplified. Category prefixes removed from tool descriptions for cleaner display.
- **Better Startup Diagnostics** — Clear warnings when required environment variables (e.g. `XAI_API_KEY`, `OLLAMA_URL`) are missing.

These changes significantly improve long-term stability, observability, and developer experience while maintaining full backward compatibility.

---

### Observability, Configuration & Performance Layer (Mai 2026)

Im Rahmen der laufenden Architektur-Härtung wurden folgende zentrale Verbesserungen implementiert:

- **Zentrale Konfiguration** (`backend/config.py`): Alle Umgebungsvariablen sind jetzt in einer immutable `Settings`-Klasse gebündelt. Das erhöht Typsicherheit, Wartbarkeit und Testbarkeit erheblich.
- **Dependency Injection**: Core Services (`AgentContext`, `Registry`, `Settings`) werden über FastAPI `Depends` injiziert. Dadurch sind Abhängigkeiten explizit und Unit-Tests deutlich einfacher.
- **Event Bus** (`backend/events.py`): Ein leichter, thread-sicherer Event Bus ermöglicht entkoppelte Reaktionen auf State-Änderungen (Persona/Skill aktiviert oder zurückgesetzt). Standardmäßig sind Logging-Subscriber aktiv.
- **Umfassende Logging-Schicht**: Detaillierte Logger für Tool-Ausführungen (`mcp.tools`), Memory-Operationen (`mcp.memory`), Prompt-Bau (`mcp.prompt`) und Event Bus (`mcp.events`).
- **Prompt-Cache mit Auto-Invalidierung** (`backend/prompt_cache.py`): Der dynamisch generierte System-Prompt wird versioniert gecacht. Bei Aktivierung einer neuen Persona oder eines Skills wird der Cache automatisch über den Event Bus invalidiert — Performance-Gewinn bei gleichbleibendem Kontext bei voller Korrektheit.

Diese Maßnahmen verbessern sowohl die **langfristige Wartbarkeit** als auch die **Beobachtbarkeit** des Systems signifikant, ohne die bestehende Architektur zu verletzen.

---

## ✨ Frontend Refactoring

> **Ziel:** Die Frontend-Architektur radikal aufräumen, vereinfachen und langfristig wartbar machen – ohne Kompromisse bei der Architekturtreue.

### Was wurde gemacht?

Nach mehreren schmerzhaften Restrukturierungen war `layout.py` zu einem monolithischen Event-Orchestrator geworden. Ziel des Refactorings war es, die klassische Trennung wiederherzustellen:

- **UI-Komposition** vs. **Event-Verdrahtung**

### Kern-Änderungen

| Bereich                    | Vorher                              | Nachher                                      |
|---------------------------|-------------------------------------|----------------------------------------------|
| **Event-Handling**        | Alles direkt in `layout.py`         | Vollständig ausgelagert in `event_wiring.py` |
| **layout.py**             | ~220 Zeilen, schwer lesbar          | < 100 Zeilen, reine Komposition              |
| **Temporäre Imports**     | Viele Workarounds                   | Komplett entfernt                            |
| **Verantwortlichkeiten**  | Vermischt                           | Klar getrennt                                |
| **Wartbarkeit**           | Mittel                              | Sehr hoch                                    |

### Neue Struktur

- **`event_wiring.py`** — Zentrale Wiring-Schicht  
  Alle `.click()`, `.then()`, `.submit()` und `.load()` Verbindungen leben jetzt in dedizierten Funktionen (`wire_persona_controls`, `wire_skill_controls`, ...).

- **`layout.py`** — Reine UI-Zusammenstellung  
  Enthält nur noch die Erstellung und Anordnung der Komponenten. Keine Event-Logik mehr.

- **Komponenten** (`*.py` in `components/`) — Bleiben fokussiert auf ihre jeweilige UI-Logik.

### Ergebnis

- ✅ Deutlich höhere **Lesbarkeit** und **Wartbarkeit**
- ✅ Keine versteckten Abhängigkeiten oder toten Code
- ✅ Volle Einhaltung der holy Architecture Rules
- ✅ Die UI bleibt „dumm“ und kommuniziert ausschließlich über `/mcp`
- ✅ Einfacher zu erweitern (neue Panels, neue Controls)

**Status:** Abgeschlossen und produktiv. Alle Logs clean, UI startet stabil, sämtliche Interaktionen (Persona, Skill, Tools, Memory) funktionieren einwandfrei.

**MCP Projektleiter** — Principal Engineer & Technical Project Lead  
*“Langfristige Stabilität > schnelle Hacks.”*

---

## Neueste Verbesserungen (Mai 2026)

### 1. Provider-Umstrukturierung & Renaming

Das Projekt wurde konsequent auf eine saubere Provider-Architektur umgestellt:

- **"grok" → "xAI"**: Vollständiges internes Renaming des primären Providers  
  - Datei `backend/providers/grok.py` → `xai.py`
  - Klasse `GrokProvider` → `XAIProvider`
  - Interner Key einheitlich `"xai"`
- **Neue Provider hinzugefügt**:
  - **OpenAI** (GPT-4o, o1 etc.)
  - **Anthropic** (Claude)
- Alle Provider nutzen jetzt die zentrale `ModelProvider`-Abstraktion (`backend/providers/base.py`)
- Sauberes Mapping in `state.py`, `core.py`, `chat_handler.py` und `prompt_builder.py`

Das System ist nun deutlich erweiterbar und zukunftssicher.

### 2. Projekt-Umbenennung

Das Projekt trägt jetzt offiziell den Namen:

**Wäärkzüüg-Chaschte 🧰**

- Gradio-UI-Titel und Browser-Tab aktualisiert
- FastAPI-App-Titel angepasst
- Alle relevanten Stellen im Code und in der Dokumentation konsistent umbenannt

### 3. Verbesserte UI-States & neue Tools

Die Benutzeroberfläche wurde deutlich stabiler und informativer:

- **Live Status-Bar** zeigt nun immer korrekt:
  - Verbindungsstatus + Tool-Anzahl
  - Aktuelle Prompt-Version
  - Aktive Persona + Skill
  - Gewähltes Modell (xAI / OpenAI / Anthropic / Ollama)
- **Neue Tools** für bessere Kontrolle:
  - `set_active_provider`
  - `get_active_provider`
  - `get_active_model`
  - `clear_active_provider`
- Automatische Synchronisation aller UI-Elemente nach Model-Wechsel, Persona- oder Skill-Aktivierung
- Verbesserter System-Prompt-Viewer mit exakter, live generierter Prompt-Anzeige
- Bessere Fehlerbehandlung und visuelles Feedback bei Tool-Ausführung

Diese Änderungen sorgen für deutlich mehr Transparenz und verhindern Desynchronisation zwischen Backend-State und UI.

---

**Zusammenfassung:**  
Wäärkzüüg-Chaschte 🧰 ist nun eine saubere, erweiterbare und professionell strukturierte Agenten-Plattform mit klarer Provider-Architektur und einer sehr stabilen Benutzeroberfläche.

*Clean single-file documentation for v1.0.0 — 2026-05-18*
