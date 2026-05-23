#!/usr/bin/env python3
""" 
Custom MCP Server - FastAPI Edition v1.0
"""

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Literal
import json
import os
import logging
from starlette.responses import StreamingResponse
from backend.tools import (
    registry,
    DEFAULT_SESSION_ID,
    refresh_default_session,
    execute_tool
)
from backend.providers import get_provider
from backend.tools.registry import registry as _registry
from backend.prompt_builder import build_dynamic_system_prompt
from backend.config import settings
from backend.dependencies import AgentContextDep, RegistryDep, SettingsDep


# ====================== LOGGING ======================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-log")


# ====================== ENVIRONMENT CHECK ======================
missing_vars = []
if not settings.XAI_API_KEY:
    missing_vars.append("XAI_API_KEY")
if not settings.OLLAMA_URL and not settings.OLLAMA_HOST:
    missing_vars.append("OLLAMA_URL / OLLAMA_HOST")

if missing_vars:
    logger.warning(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")


# ====================== STARTUP INTEGRITY CHECK ======================
logger.info("Running startup integrity check...")

try:
    from backend.tools import loader
    registered_names = set(t.name for t in registry.get_all_definitions())
    integrity = loader.get_integrity_report(registered_names)
    
    if integrity["healthy"]:
        logger.info(f"✅ Tool Integrity: healthy ({integrity['total_registered_tools']} tools / {integrity['total_discovered_executors']} executors)")
    else:
        logger.warning("⚠️  Tool Integrity issues detected:")
        if integrity["missing_executors"]:
            logger.warning(f"   Missing executors for: {integrity['missing_executors']}")
        if integrity["missing_definitions"]:
            logger.warning(f"   Executors without definition: {integrity['missing_definitions']}")
except Exception as e:
    logger.error(f"Startup integrity check failed: {e}")


# ====================== CONFIG ======================
MCP_API_KEY = settings.MCP_API_KEY
AUTH_ENABLED = bool(MCP_API_KEY and MCP_API_KEY != "your_mcp_authtoken_here")
MCP_PUBLIC_URL = settings.MCP_PUBLIC_URL


# ====================== MODELS ======================
class ToolDefinition(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]


class MCPRequest(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: Optional[Any] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPError(BaseModel):
    code: int
    message: str


class MCPResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: Optional[Any] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[MCPError] = None


class ToolCallParams(BaseModel):
    name: str
    arguments: Optional[Dict[str, Any]] = Field(default_factory=dict)


# ====================== APP ======================
app = FastAPI(title="MCP-Server v1.0", version="1.0.0")


app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/")
async def root():
    try:
        from backend.tools import loader
        registered_names = set(t.name for t in registry.get_all_definitions())
        integrity = loader.get_integrity_report(registered_names)
        integrity_status = "healthy" if integrity["healthy"] else "issues_found"
    except Exception:
        integrity_status = "unknown"

    return {
        "status": "running",
        "mcp_endpoint": "/mcp",
        "auth_enabled": AUTH_ENABLED,
        "tools": len(registry.get_all_definitions()),
        "integrity": integrity_status
    }


@app.get("/.well-known/oauth-authorization-server")
async def oauth_auth_server():
    return {"issuer": "https://mcp-server", "authorization_endpoint": "/authorize", "token_endpoint": "/token", "response_types_supported": ["code"], "grant_types_supported": ["authorization_code"], "token_endpoint_auth_methods_supported": ["none"], "scopes_supported": ["mcp"]}


@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected():
    return {"resource": "/mcp", "authorization_servers": ["https://mcp-server"], "scopes_supported": ["mcp"]}


@app.get("/mcp")
async def mcp_info():
    return {"message": "MCP endpoint ready – use POST with JSON-RPC"}


@app.post("/mcp")
async def mcp_handler(
    request: Request,
    authorization: Optional[str] = Header(None),
    ctx: AgentContextDep = None,
    reg: RegistryDep = None,
    cfg: SettingsDep = None,
):
    if AUTH_ENABLED:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Missing or invalid Authorization header")
        if authorization.split(" ", 1)[1] != MCP_API_KEY:
            raise HTTPException(403, "Invalid API key")

    body = await request.json()
    logger.info(f"Received MCP request: {json.dumps(body, indent=2)}")

    if not body or not isinstance(body, dict):
        return MCPResponse(id=None, error=MCPError(code=-32700, message="Empty request"))

    if "method" not in body:
        if "name" in body:
            body["method"] = "tools/call"
        else:
            return MCPResponse(id=None, error=MCPError(code=-32700, message="Missing method field"))

    try:
        req = MCPRequest(**body)
    except Exception as e:
        return MCPResponse(id=body.get("id"), error=MCPError(code=-32700, message=f"Parse error: {str(e)}"))

    method = req.method
    params = req.params or {}
    req_id = req.id

    try:
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "mcp-fastapi-v1", "version": "1.0.0"}}
        elif method == "notifications/initialized":
            result = {}
        elif method == "tools/list":
            tools_serialized = []
            for t in registry.get_all_definitions():
                try:
                    tools_serialized.append(t.model_dump())
                except Exception as e:
                    logger.warning(f"Tool serialization failed for {getattr(t, 'name', 'unknown')}: {e}")
            result = {"tools": tools_serialized}
        elif method == "tools/call":
            tool = ToolCallParams(**params)
            result = registry.execute(tool.name, tool.arguments or {})
        elif method.startswith("tools/"):
            tool_name = method.split("/", 1)[1]
            args = params.get("arguments", {}) if isinstance(params, dict) else {}
            result = registry.execute(tool_name, args)
        elif method in ["resources/list", "prompts/list"]:
            result = {"resources": [], "prompts": []}
        elif method == "ping":
            result = {"status": "ok"}
        elif method == "prompts/get_dynamic":
            requested_model = (params or {}).get("model")

            tools_for_prompt = [
                {
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema
                    },
                    "category": getattr(t, "category", "core")
                }
                for t in reg.get_all_definitions()
            ]

            # === Dependency Injection (jetzt sauber) ===
            try:
                active_persona = ctx.active_persona if ctx else None
                active_skill = ctx.active_skill if ctx else None
                active_model = ctx.active_model if ctx else None
            except Exception as e:
                logger.error(f"Error getting context via dependency: {e}")
                active_persona = None
                active_skill = None
                active_model = None

            effective_model = requested_model or active_model

            try:
                result = build_dynamic_system_prompt(
                    model=effective_model,
                    tools=tools_for_prompt,
                    active_persona=active_persona,
                    active_skill=active_skill
                )
            except Exception as e:
                logger.error(f"Error building dynamic prompt: {e}")
                result = {"prompt": "Error building prompt", "version": "error"}
        elif method == "models/chat":
            from backend.providers import get_provider
            # Erwartet: {"provider": "grok" | "ollama", "messages": [...], "tools": [...], "temperature": 0.7, ...}
            provider_name = (params or {}).get("provider") or (params or {}).get("model", "grok")
            provider = get_provider(provider_name)

            if not provider:
                return MCPResponse(
                    id=req_id,
                    error=MCPError(code=-32602, message=f"Unknown provider: {provider_name}")
                )

            try:
                # Sauberer await (kein asyncio.run mehr!)
                result = await provider.chat(
                    messages=(params or {}).get("messages", []),
                    tools=(params or {}).get("tools"),
                    temperature=(params or {}).get("temperature", 0.7),
                    max_tokens=(params or {}).get("max_tokens"),
                    stream=False
                )
                return MCPResponse(id=req_id, result=result)

            except Exception as e:
                logger.error(f"models/chat error for provider {provider_name}: {e}")
                return MCPResponse(
                    id=req_id,
                    error=MCPError(code=-32603, message=f"Provider error: {str(e)}")
                )

        else:
            return MCPResponse(id=req_id, error=MCPError(code=-32601, message=f"Method not found: {method}"))

        return MCPResponse(id=req_id, result=result)

    except Exception as e:
        logger.error(f"Error executing {method}: {e}")
        return MCPResponse(id=req_id, error=MCPError(code=-32603, message=str(e)))


@app.post("/mcp/stream")
async def mcp_stream_handler(request: Request):
    """
    Improved streaming endpoint using Server-Sent Events (SSE) style.
    Currently supports simple text streaming without tool calling.
    """
    body = await request.json()
    params = body.get("params", {}) if isinstance(body, dict) else {}

    provider_name = params.get("provider") or params.get("model", "grok")
    provider = get_provider(provider_name)

    if not provider:
        return {"error": f"Unknown provider: {provider_name}"}

    messages = params.get("messages", [])
    tools = params.get("tools")
    temperature = params.get("temperature", 0.7)
    max_tokens = params.get("max_tokens")

    try:
        # Provider liefert den passenden Stream zurück
        stream = await provider.chat(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )

        async def stream_generator():
            if provider.streaming_type == "openai":
                # OpenAI-kompatibles Streaming (Grok + OpenAI)
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            elif provider.streaming_type == "ollama":
                # Ollama natives Streaming
                for chunk in stream:
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content

            else:
                # Fallback für zukünftige Provider (z.B. anthropic, google)
                yield f"[Streaming für '{provider.streaming_type}' noch nicht implementiert]"

        return StreamingResponse(
            stream_generator(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache"}
        )

    except Exception as e:
        logger.error(f"Streaming error for provider {provider_name}: {e}")
        return {"error": str(e)}


# ====================== DYNAMIC OPENAPI SPEC ======================
def generate_openapi_spec():
    tools_list = "\n".join(
        f"- **{tool.name}**: {tool.description}\n  Input: {json.dumps(tool.inputSchema, indent=2)}"
        for tool in registry.get_all_definitions()
    )

    public_url = MCP_PUBLIC_URL

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "MCP-Server",
            "version": "1.0.0",
            "description": f"""FastAPI-based MCP server using JSON-RPC 2.0.

**Available Tools:**
{tools_list}

Use the single POST /mcp endpoint with JSON-RPC 2.0 format.
""",
            "contact": {"name": "Grok MCP"}
        },
        "servers": [
            {"url": public_url, "description": "Current ngrok tunnel"}
        ],
        "paths": {
            "/mcp": {
                "post": {
                    "summary": "MCP JSON-RPC Endpoint",
                    "description": "Handles initialize, tools/list, tools/call, and all other MCP methods.",
                    "operationId": "mcpHandler",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/MCPRequest"}}}
                    },
                    "responses": {
                        "200": {
                            "description": "MCP Response",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/MCPResponse"}}}
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "MCPRequest": {
                    "type": "object",
                    "required": ["jsonrpc", "method"],
                    "properties": {
                        "jsonrpc": {"type": "string", "example": "2.0"},
                        "id": {"type": ["string", "integer", "null"], "example": 1},
                        "method": {"type": "string", "example": "tools/list"},
                        "params": {"type": "object"}
                    }
                },
                "MCPResponse": {
                    "type": "object",
                    "properties": {
                        "jsonrpc": {"type": "string"},
                        "id": {"type": ["string", "integer", "null"]},
                        "result": {"type": "object"},
                        "error": {"type": "object", "nullable": True}
                    }
                }
            }
        },
        "x-mcp-tools": [tool.model_dump() for tool in registry.get_all_definitions()]
    }


@app.get("/mcp/openapi.json", tags=["OpenAPI"])
async def get_openapi_spec():
    return generate_openapi_spec()


@app.get("/health")
async def health_check(
    ctx: AgentContextDep,
    reg: RegistryDep,
    cfg: SettingsDep
):
    """Detailed health endpoint for monitoring and orchestration."""
    try:
        from backend.tools import loader

        registered_names = set(t.name for t in reg.get_all_definitions())
        integrity = loader.get_integrity_report(registered_names)

        # Aktueller Agent-Kontext (jetzt über Dependency Injection)
        active_persona = ctx.active_persona.get("name") if ctx.active_persona else None
        active_skill = ctx.active_skill.get("name") if ctx.active_skill else None

        return {
            "status": "healthy" if integrity["healthy"] else "degraded",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "tools": {
                "registered": integrity["total_registered_tools"],
                "executors_discovered": integrity["total_discovered_executors"],
                "healthy": integrity["healthy"]
            },
            "context": {
                "active_persona": active_persona,
                "active_skill": active_skill
            },
            "integrity": integrity,
            "version": "1.0.0",
            "config": {
                "xai_model": cfg.XAI_MODEL,
                "ollama_model": cfg.OLLAMA_MODEL,
                "has_xai_key": cfg.has_xai_key
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8321)