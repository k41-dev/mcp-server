# Wäärkzüüg-Chaschte

**Production-grade autonomous agent server** with JSON-RPC MCP endpoint, persistent vector memory, dynamic persona/skill injection, and multi-provider support (Grok, Ollama, OpenAI, Anthropic).

Built under strict architectural discipline for long-term stability, clean separation of concerns, and zero-surprise deployments.

**Current Version:** 1.0.0 (May 2026)  
**Status:** Stable foundational release with hardened architecture

---

## Prerequisites

### Required
- **Docker** + **Docker Compose** (recommended way to run)
- **Python 3.12+** (for local development)
- **XAI API Key** — for Grok models (`XAI_API_KEY`)
- **Ollama** running locally or accessible — for local models + embeddings (`nomic-embed-text`)

### Optional but Recommended
- **ngrok** authtoken + custom domain (for public HTTPS access)
- **SearXNG** instance (for web search)
- **Browserless** instance (for reliable web browsing)

### Environment Variables (`.env`)
Minimum required:
```env
XAI_API_KEY=your_key_here
OLLAMA_MODEL=llama3.1:latest
OLLAMA_EMBED_MODEL=nomic-embed-text
MCP_PUBLIC_URL=http://localhost:8321
```

---

## INFO - IMPORTANT

So basically you have to create new sessions with the corresponding tool atm.
Memory, Persona, Skill and Provider are part of the AgentContext, so we have session-specific
stats and could setup sessions with distict settings. Also, when switching a session,
the Context is saved, so you can switch everything in the session and then move to another.

The 42 tools are a foundation and this platform can test those. you can write a new executor,
set new definitions in the directory and everything is loaded automatic through the registry.

I plan to implement better UI-feeling. UI uses mcp-calls mostly, so you have a strict architecture,
separating the backend from the frontend.

Also session-creation and displaying multiple sessions, having an agent run longer, is planned.
Anthropic and OpenAI, aswell the normal cli client might not work yet, since I just did a 
simple implementation and no tweaks (I have no api-keys for that). But ollama and grok
just work fine for me atm. Anthropic has a different SDK, so this might take a bit.

All code was vibecoded with the grok-4.3 model, I just asked the Expert sometimes, when we had
to get a different opinion on certain things.

Best way to setup is with uv, which is a very useful packet-manager. You simply uv sync and get
all the packages.

Docker is atm a hardcoded subnet called app-net with static ips, so create this subnet before or remove
the static parts. 
If you want to add real websearch and browsepage-tool, feel free to look at searxng and browserless, 
which you can add to the docker-compose file. I have setup env-vars were you can add the container-
adress. 

## Quick Start (Recommended)

```bash
# 1. Clone and prepare environment
git clone <repository-url>
cd mcp-server
cp env.example.txt .env
# Edit .env with your keys

# 2. Start everything
docker compose up --build -d

# 3. Access points
# Gradio UI:   http://localhost:7860
# MCP Server:  http://localhost:8321/mcp
# Health:      curl http://localhost:8321/
```

After any code change in `backend/` or `frontend/`:
```bash
docker compose build <service> && docker compose up -d <service>
# Then clean caches in the container:
docker compose exec <service> find /app -type d -name __pycache__ -exec rm -rf {} +
```

---

## Project Structure

```
mcp-agent-platform/
├── backend/                      # Core business logic (Single Source of Truth)
│   ├── server.py                 # FastAPI + JSON-RPC 2.0 MCP endpoint
│   ├── prompt_builder.py         # Dynamic system prompt engine + versioning
│   ├── memory.py                 # SQLite + sqlite-vec persistent memory
│   ├── config.py                 # Immutable Settings (central config)
│   ├── tools/
│   │   ├── registry.py           # Tool registration + auto-loading from JSON
│   │   ├── loader.py             # Automatic executor discovery + integrity checks
│   │   ├── context.py            # AgentContext (single source for persona/skill/session)
│   │   ├── state.py              # Centralized transient state (persona/skill/provider)
│   │   ├── definitions/          # All tool definitions (JSON, categorized)
│   │   │   ├── core/             # Foundational tools
│   │   │   ├── memory/           # Memory tools
│   │   │   ├── persona/          # Persona management
│   │   │   ├── skill/            # Skill activation
│   │   │   └── web/              # Web search & browse
│   │   └── executors/            # Python implementations (auto-discovered)
│   ├── providers/                # LLM Provider abstraction (xai, ollama, openai, anthropic)
│   └── events.py                 # Lightweight Event Bus for state changes
│
├── frontend/                     # Pure UI layer (never imports backend/)
│   ├── gradio_app.py             # Gradio 6 entry point
│   ├── layout.py                 # UI composition only
│   ├── event_wiring.py           # All event handlers (clean separation)
│   ├── components/               # Reusable UI components
│   └── client.py                 # CLI agent (Grok + Ollama loops)
│
├── prompts/
│   ├── personas/                 # Persona definitions (.md)
│   └── skills/                   # Structured Skills (.md) — higher priority than Personas
│
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.ui
├── pyproject.toml
├── requirements.txt
└── README.md
```

**Core Architectural Rules (non-negotiable):**
- `backend/` = Server, Tools, Memory, Prompt Logic, Business Rules
- `frontend/` = **Dumb UI only** — communicates **exclusively** via MCP JSON-RPC (`/mcp`)
- No backend imports in the frontend
- All tools = JSON definition + auto-discovered executor
- Skills always have priority over Personas in prompt injection

---

## Core Functions & Features

### 1. MCP JSON-RPC Server (`backend/server.py`)
- FastAPI-based JSON-RPC 2.0 endpoint at `/mcp`
- Full MCP protocol support (`initialize`, `tools/list`, `tools/call`, etc.)
- Streaming endpoint `/mcp/stream`
- Health checks and dynamic OpenAPI spec

### 2. Dynamic System Prompt Engine (`prompt_builder.py`)
- Loads base prompt per model family (Grok / Ollama / OpenAI / Anthropic)
- Injects current tools (grouped by category)
- Injects active **Skill** (highest priority) + **Persona**
- Computes stable version hash (`persona|skill|tools_count|model`)
- Automatic cache invalidation via Event Bus on state changes

### 3. Tool System (42 Tools)
All tools are defined in `backend/tools/definitions/{category}/*.json` and implemented in `executors/`.

**Categories:**
- **core**: `get_server_info`, `get_current_time`, `calculate`, `get_current_context`, `validate_tools`, `reload_executors`...
- **memory**: `store_memory`, `recall_memory`, `list_memories`, `clear_memory`, `add_chat_turn`, `full_reset`...
- **persona**: `list_personas`, `set_active_persona`, `get_active_persona`, `clear_active_persona`...
- **skill**: `list_skills`, `execute_skill` (recommended), `set_active_skill`, `get_active_skill`...
- **web**: `web_search` (SearXNG), `browse_page` (Browserless or direct)

Tools are **auto-discovered** on startup with integrity validation.

### 4. Persistent Memory Layer
- Hybrid **SQLite + sqlite-vec** with **Ollama `nomic-embed-text`** embeddings (768 dim)
- Session-aware long-term memory + chat history
- Semantic recall with vector search + text fallback
- `full_reset` for nuclear wipe

### 5. Persona & Skill System
- **Personas** (`prompts/personas/`): Professor, Comedian, Pirate, Detective, etc.
- **Skills** (`prompts/skills/`): Structured workflows with higher priority (e.g. `comic_glitch_creator` with full ReAct + CoT)
- Activation via tools or UI — content is injected into every system prompt

### 6. Multi-Provider LLM Support
Clean abstraction in `backend/providers/`:
- **xAI (Grok)** — native tool calling
- **Ollama** — native tools + defensive raw-JSON fallback parser
- **OpenAI**
- **Anthropic (Claude)**

Provider can be switched at runtime via UI or `set_active_provider` tool.

### 7. Gradio Web UI (`frontend/`)
Clean, modern interface with:
- Live status bar (connection, prompt version, active persona/skill, session, model selector)
- Full-height chat with tool execution indicators and streaming
- System Prompt viewer (live injected prompt + version)
- Persona & Skill controls with intensity
- Tools panel (dropdown + insert)
- Memory panel (LT memory, chat history, full reset)
- Session management
- Fully responsive + custom dark theme

**Important:** The UI is completely decoupled — it only talks to the MCP server.

### 8. CLI Agent (`frontend/client.py`)
Full multi-turn agent loops for both Grok and Ollama:
```bash
uv run client.py grok "What is the current server status?"
uv run client.py ollama "Erzähl mir etwas über den Bodensee" --stream
```

Automatically loads recent chat history + relevant long-term memories.

### 9. Observability & Maintainability Layer
- Centralized immutable `Settings`
- Dependency Injection (FastAPI `Depends`)
- Lightweight Event Bus for state changes (Persona/Skill activated, context cleared)
- Automatic Prompt Cache with Event-driven invalidation
- Detailed structured logging across all components
- Tool integrity checks on startup

---

## Development Philosophy (MCP Projektleiter)

This project follows strict principles:

1. **Architecture First** — Long-term maintainability > clever hacks
2. **Strict Layering** — Backend and Frontend are strictly separated
3. **Surgical Changes** — Only touch what is necessary
4. **Auto-Discovery** — New tools, personas, and skills require minimal boilerplate
5. **Zero Surprise** — After any change, the system should remain predictable
6. **Defensive Ollama Handling** — Never touch the Grok path when fixing Ollama issues

---

## License

MIT License — see `LICENSE` file.

---

**Maintained with discipline by the MCP Projektleiter**  
*“Langfristige Stabilität und Wartbarkeit stehen über schnellen Features.”*

For detailed technical documentation of individual components, refer to the source files and their docstrings.
