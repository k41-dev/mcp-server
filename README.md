# MCP Agent Platform v1.0.0

**Production-grade autonomous agent server** with JSON-RPC MCP endpoint, persistent vector memory, dynamic persona/skill injection, and dual-model support (Grok-4.3 + Ollama).

Built and maintained under strict architectural discipline for long-term stability, zero-surprise deployments, and clean separation of concerns.

---

## Executive Summary

This platform provides a complete, containerized environment for running a tool-calling AI agent:

- **MCP Server** (`backend/server.py`): FastAPI-based JSON-RPC 2.0 endpoint (`/mcp`) implementing a custom MCP protocol.
- **27+ Tools**: Core utilities, web search/browse (SearXNG + Browserless), persistent memory, persona management, and skill activation.
- **Dynamic System Prompts**: `prompt_builder.py` composes versioned prompts on-the-fly, injecting current tools + active persona + active skill (skills have priority).
- **Persistent Memory**: Hybrid SQLite + `sqlite-vec` + Ollama `nomic-embed-text` embeddings for semantic long-term recall.
- **Gradio UI** (`frontend/gradio_app.py`): Full-featured chat interface with live controls — **never imports backend code**.
- **CLI Client** (`client.py`): Scriptable agent loops for Grok and Ollama with full tool calling and memory integration.
- **Docker Compose**: Three services (`mcp-server`, `agent-ui`, `ngrok`) with healthchecks and volume mounts for prompts/data.

The architecture was hardened through multiple painful restructurings. The guiding principle is **long-term maintainability > clever hacks**.

---

## Architecture (Holy Rules)

### Strict Layering
```
backend/          → Server, Tools, Memory, Prompt Logic, Business Rules
frontend/         → Pure UI layer (Gradio). **MUST NOT** import anything from backend/
```

- All UI ↔ Backend communication happens **exclusively** over the MCP JSON-RPC endpoint (`POST /mcp`).
- `prompt_builder.py` is the **Single Source of Truth** for system prompts.
- `backend/tools/registry.py` + JSON definitions in `definitions/` are the Single Source of Truth for tools.
- Docker Compose is the source of truth for runtime. Local edits without rebuild are meaningless.

### Critical Components

| Component              | File(s)                          | Responsibility |
|------------------------|----------------------------------|----------------|
| MCP JSON-RPC Handler   | `backend/server.py`             | `/mcp` endpoint, method routing, auth |
| Tool Registry & Factory| `backend/tools/registry.py`     | Auto-loads JSON defs + executors from `definitions/` subdirs |
| Tool Executors         | `backend/tools/executors/*.py`  | `core.py`, `web.py`, `memory.py`, `persona.py`, `skill.py` |
| Memory Layer           | `backend/memory.py`             | Sessions, chat history, long-term facts + vector search |
| Prompt Engine          | `backend/prompt_builder.py`     | Dynamic prompt + versioning (MD5 hash of persona+skill+tool count) |
| Skill Discovery        | `backend/skill_factory.py`      | Scans `prompts/skills/*.md` |
| Gradio UI              | `frontend/gradio_app.py`        | Chat, controls, **dumb client only** |
| CLI Agent              | `client.py`                     | Full multi-turn tool loops + memory context |

### Tool Calling Strategy

- **Grok path**: Native `tools` + `tool_choice="auto"` via OpenAI-compatible SDK. Clean and stable.
- **Ollama path**: Native `tools` parameter + **defensive fallback** — if model emits raw JSON instead of structured tool calls, it is parsed and executed. This was learned the hard way.

**Never** touch the Grok path when fixing Ollama issues.

---

## Available Tools (Current Registry)

**Core (6)**
- `get_current_time`, `echo`, `get_random_number`, `calculate` (safe AST eval), `get_server_info`, `get_prompt_status`

**Web (2)**
- `web_search` (SearXNG), `browse_page` (Browserless or direct with BeautifulSoup)

**Memory (8)**
- `store_memory`, `recall_memory`, `list_memories`, `clear_memory`
- `add_chat_turn`, `list_chat_history`, `clear_chat_history`, `full_reset`

**Persona (4)**
- `list_personas`, `set_active_persona`, `get_active_persona`, `clear_active_persona`

**Skill (5)**
- `list_skills`, `execute_skill` (preferred), `set_active_skill`, `get_active_skill`, `clear_active_skill`

**Total: 27 tools** (loaded dynamically from `definitions/*.json`).

---

## Personas & Skills

### Personas (`prompts/personas/`)
- `professor.md` — Patient, precise academic
- `comedian.md` — Sarcastic stand-up (Rusty Quill)
- `pirate.md` — Theatrical Captain Silas Blackwake
- `detective.md` — Calm Inspector Margot Vale

### Skills (`prompts/skills/`)
- `comic_glitch_creator.md` — Full ReAct + Chain-of-Thought workflow for generating 10 detailed comic prompts (Bill Sienkiewicz + GlitchArt style). **Higher priority than any persona**.

**Activation rules** (enforced in prompt):
1. Skills > Personas
2. Core Agent rules (tool usage, truth, safety) **always** override personality instructions.
3. Use `execute_skill` tool to activate structured behavior.

---

## Quick Start (Docker — Recommended)

```bash
# 1. Prepare environment
cp env.example.txt .env
# Edit .env — at minimum set:
#   XAI_API_KEY=sk-...
#   OLLAMA_MODEL=llama3.1:latest   (or your preferred local model)
#   NGROK_AUTHTOKEN=...            (optional but recommended for public URL)

# 2. Start everything
docker compose up --build -d

# 3. Access points
# Gradio UI:     http://localhost:7860
# MCP Endpoint:  http://localhost:8321/mcp   (or your ngrok URL)
# Health:        curl http://localhost:8321/
```

**After any backend change**:
```bash
docker compose build mcp-server && docker compose up -d mcp-server
```

**After any frontend change**:
```bash
docker compose build agent-ui && docker compose up -d agent-ui
```

**Always** after structural changes:
```bash
docker compose exec mcp-server find /app -type d -name __pycache__ -exec rm -rf {} +
docker compose exec agent-ui find /app -type d -name __pycache__ -exec rm -rf {} +
```

---

## Gradio UI Tour

The UI is deliberately "dumb" — all intelligence lives behind the MCP endpoint.

**Left Column — Chat**
- Full conversation with avatar
- Model switch (Grok ↔ Ollama) — instantly changes system prompt
- Send button + Enter support

**Right Column — Controls**
- **📜 System Prompt** (live viewer + refresh) — shows exactly what the model currently sees (including injected persona/skill)
- **🎭 Persona** — dropdown (auto-loaded), intensity slider, Apply/Reset
- **🛠️ Skill** — dropdown (auto-loaded), Activate/Reset (uses `execute_skill`)
- **🛠️ Available Tools** — searchable dropdown + description + "Insert Tool" button (great for testing)
- **🧠 Memory** — Show/Clear long-term memory, Show/Clear chat history, Full Nuclear Reset

All controls call MCP tools under the hood and refresh the dynamic prompt automatically.

---

## CLI Usage Examples

```bash
# Grok with full tool calling + memory
uv run client.py grok "What is the current server status and latest AI news?"

# Ollama (local) with streaming
uv run client.py ollama "Store the fact that I prefer dark mode" --stream

# Direct MCP inspection
uv run client.py mcp-list
uv run client.py mcp-call get_server_info
```

---

## Environment Variables (`.env`)

| Variable                | Purpose                              | Required |
|-------------------------|--------------------------------------|----------|
| `XAI_API_KEY`           | xAI Grok access                      | Yes (for Grok) |
| `XAI_MODEL`             | `grok-4.3` (default)                 | No |
| `OLLAMA_URL`            | Auto-detected (Docker vs host)       | No |
| `OLLAMA_MODEL`          | e.g. `llama3.1:latest`               | Yes (for Ollama) |
| `OLLAMA_EMBED_MODEL`    | `nomic-embed-text`                   | No |
| `MCP_PUBLIC_URL`        | Public ngrok URL                     | Recommended |
| `NGROK_AUTHTOKEN`       | ngrok token                          | For public access |
| `SYSTEM_PROMPT_GROK`    | Filename in `prompts/`               | No |
| `SYSTEM_PROMPT_OLLAMA`  | Filename in `prompts/`               | No |

---

## Development & Debugging Rules (MCP Projektleiter Doctrine)

1. **Never** import anything from `backend/` inside `gradio_app.py` or any frontend file.
2. **Always** ask: "Does this change require a container rebuild?"
3. After **any** Python structural change → delete `__pycache__` in **both** containers.
4. Ollama tool-calling fixes belong **only** in the `else` (Ollama) block of `chat_with_agent` / `run_ollama_agent`. Never touch Grok path.
5. Prefer **small, targeted edits** over large replacements.
6. When in doubt, restore a known-good state first, then iterate.

---

## Current Status & Known Issues (v1.1.0)

**Working reliably**:
- Grok tool calling (native)
- Ollama tool calling (with JSON fallback)
- Memory (vector + text)
- Dynamic prompt versioning
- Persona/Skill activation & injection
- Docker networking & healthchecks

**Needs attention** (incremental fixes planned):
- `persona.py:get_active_persona` contains undefined variable references (copy-paste artifact from restructuring).
- Some executor files in `attachments/` appear duplicated; the canonical versions live under `backend/tools/executors/`.
- `prompt_builder.py` references `.txt` filenames in env vars while actual files are `.md` — minor.
- `get_prompt_status` tool has import issues in some contexts.

These are tracked and will be addressed with minimal-invasive patches only.

---

## Why This Architecture Exists

Previous versions suffered from:
- UI importing backend logic → container rebuild hell
- Over-aggressive global replacements breaking tool calling
- Ollama treated identically to Grok → fragile JSON output
- No versioned prompts → silent drift when personas/skills changed

The current design eliminates all of the above.

---

## License & Credits

Internal project. Built with ❤️ for reliability and clean engineering.

**MCP Projektleiter** — Principal Engineer & Technical Project Lead  
*“Langfristige Stabilität > schnelle Hacks.”*

---

*Generated with architectural discipline on 2026-05-16.*