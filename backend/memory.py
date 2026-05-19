#!/usr/bin/env python3
"""
memory.py - Persistent Chat Memory with Ollama Embeddings + sqlite-vec
"""

import os
import sqlite3
import datetime
import requests
from pathlib import Path
from backend.config import settings
from typing import List, Dict, Any, Optional
import numpy as np
import logging


logger = logging.getLogger("mcp.memory")

try:
    import sqlite_vec
    HAS_SQLITE_VEC = True
except ImportError:
    HAS_SQLITE_VEC = False

_MEMORY_INITIALIZED = False
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "chat_memory.db"

# ====================== OLLAMA CONFIG (smart host detection) ======================
import socket


def _detect_ollama_url() -> str:
    """Choose correct Ollama URL depending on environment.
    - Inside Docker → host.docker.internal works
    - On host / native Linux → localhost
    """
    env_url = settings.OLLAMA_URL
    if env_url:
        return env_url

    # Try host.docker.internal first (Docker Desktop / configured Linux)
    try:
        socket.gethostbyname("host.docker.internal")
        return "http://host.docker.internal:11434"
    except socket.gaierror:
        pass

    # Fallback to localhost (host machine or plain Linux)
    return "http://localhost:11434"

OLLAMA_URL = _detect_ollama_url()
OLLAMA_EMBED_MODEL = settings.OLLAMA_EMBED_MODEL

# 768 dimensions for nomic-embed-text (change if using a different model)
EMBEDDING_DIM = 768


def get_ollama_embedding(text: str) -> Optional[List[float]]:
    """Get embedding from local Ollama. Returns None on failure."""
    if not text or not text.strip():
        return None
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": OLLAMA_EMBED_MODEL, "prompt": text},
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("embedding")
    except Exception as e:
        print(f"⚠️ Ollama embedding failed ({OLLAMA_EMBED_MODEL} @ {OLLAMA_URL}): {e}")
        print("   → Tip: Make sure Ollama is running and the model is pulled: `ollama pull nomic-embed-text`")
        return None


def get_embedding(text: str) -> Optional[List[float]]:
    """Primary embedding function — only uses Ollama."""
    return get_ollama_embedding(text)


# ====================== DATABASE ======================
def get_db_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    if HAS_SQLITE_VEC:
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
        except Exception as e:
            print(f"⚠️ sqlite-vec load failed: {e}")
    return conn


def init_db():
    # Ensure the data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT DEFAULT 'default',
            created_at TEXT NOT NULL,
            last_active TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS long_term_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            fact TEXT NOT NULL,
            source TEXT DEFAULT 'agent',
            timestamp TEXT NOT NULL,
            embedding BLOB,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    """)

    if HAS_SQLITE_VEC:
        try:
            cur.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_memories 
                USING vec0(
                    memory_id INTEGER PRIMARY KEY,
                    embedding FLOAT[{EMBEDDING_DIM}]
                )
            """)
        except Exception as e:
            print(f"Vec table note: {e}")

    conn.commit()
    conn.close()
    global _MEMORY_INITIALIZED
    if not _MEMORY_INITIALIZED:
        print(f"✅ Ollama Vector Memory ready (model={OLLAMA_EMBED_MODEL}, dim={EMBEDDING_DIM})")
        _MEMORY_INITIALIZED = True


# ====================== SESSION & MEMORY ======================
def get_or_create_session(name: str = "default") -> int:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM sessions WHERE name = ? ORDER BY last_active DESC LIMIT 1", (name,))
    row = cur.fetchone()
    if row:
        session_id = row["id"]
        now = datetime.datetime.utcnow().isoformat() + "Z"
        cur.execute("UPDATE sessions SET last_active = ? WHERE id = ?", (now, session_id))
    else:
        now = datetime.datetime.utcnow().isoformat() + "Z"
        cur.execute(
            "INSERT INTO sessions (name, created_at, last_active) VALUES (?, ?, ?)",
            (name, now, now)
        )
        session_id = cur.lastrowid
    conn.commit()
    conn.close()
    return session_id


def add_message(session_id: int, role: str, content: str):
    conn = get_db_connection()
    cur = conn.cursor()
    now = datetime.datetime.utcnow().isoformat() + "Z"
    cur.execute(
        "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, role, content, now)
    )
    cur.execute("UPDATE sessions SET last_active = ? WHERE id = ?", (now, session_id))
    conn.commit()
    conn.close()


def get_recent_messages(session_id: int, limit: int = 30) -> List[Dict[str, str]]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?",
        (session_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"], "timestamp": row["timestamp"]} for row in rows]


def store_long_term_memory(
    session_id: int, 
    fact: str, 
    source: str = "agent",
    embedding: Optional[List[float]] = None
) -> int:
    if embedding is None:
        embedding = get_embedding(fact)

    conn = get_db_connection()
    cur = conn.cursor()
    now = datetime.datetime.utcnow().isoformat() + "Z"

    embedding_blob = None
    if embedding:
        embedding_blob = np.array(embedding, dtype=np.float32).tobytes()

    cur.execute(
        "INSERT INTO long_term_memories (session_id, fact, source, timestamp, embedding) VALUES (?, ?, ?, ?, ?)",
        (session_id, fact, source, now, embedding_blob)
    )
    memory_id = cur.lastrowid

    if embedding and HAS_SQLITE_VEC:
        try:
            cur.execute(
                "INSERT INTO vec_memories (memory_id, embedding) VALUES (?, ?)",
                (memory_id, np.array(embedding, dtype=np.float32).tobytes())
            )
        except Exception as e:
            print(f"Vec insert warning: {e}")

    conn.commit()
    conn.close()
    logger.info(f"🧠 Memory gespeichert (ID: {memory_id}) | Source: {source}")
    return memory_id


def recall_memories(session_id: int, query: str = "", limit: int = 8) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()

    query_embedding = get_embedding(query) if query else None

    if query_embedding and HAS_SQLITE_VEC:
        try:
            cur.execute(
                """
                SELECT memory_id, distance 
                FROM vec_memories 
                WHERE embedding MATCH ? 
                ORDER BY distance 
                LIMIT ?
                """,
                (np.array(query_embedding, dtype=np.float32).tobytes(), limit)
            )
            vec_results = cur.fetchall()
            if vec_results:
                memory_ids = [r["memory_id"] for r in vec_results]
                placeholders = ",".join("?" * len(memory_ids))
                cur.execute(
                    f"SELECT fact, source, timestamp FROM long_term_memories WHERE id IN ({placeholders}) AND session_id = ?",
                    (*memory_ids, session_id)
                )
                rows = cur.fetchall()
                conn.close()
                return [{"fact": r["fact"], "source": r["source"], "timestamp": r["timestamp"]} for r in rows]
        except Exception as e:
            print(f"Vector search fallback to text search: {e}")

    # Fallback to simple text search (LIKE)
    if query:
        cur.execute(
            "SELECT fact, source, timestamp FROM long_term_memories WHERE session_id = ? AND fact LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (session_id, f"%{query}%", limit)
        )
    else:
        cur.execute(
            "SELECT fact, source, timestamp FROM long_term_memories WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
            (session_id, limit)
        )
    rows = cur.fetchall()
    conn.close()
    return [{"fact": r["fact"], "source": r["source"], "timestamp": r["timestamp"]} for r in rows]


def list_all_memories(session_id: int) -> List[Dict[str, Any]]:
    return recall_memories(session_id, query="", limit=50)


def clear_long_term_memory():
    """Clears only long-term semantic memory (facts & preferences).
    Does NOT touch conversation history."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM long_term_memories")
    conn.commit()
    conn.close()
    logger.warning("🗑️ Long-term Memory wurde geleert!")
    print("🗑️ Long-term memory cleared (facts & preferences wiped).")


def clear_chat_history():
    """Clears ONLY conversation history using DROP + CREATE (most reliable method).
    Does NOT touch long-term memory."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("DROP TABLE IF EXISTS messages")
    cur.execute("""
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()
    logger.warning("🗑️ Chat History wurde geleert!")
    print("🗑️ Chat history cleared (conversation turns wiped).")


def full_reset():
    """Nuclear wipe: deletes the entire chat_memory.db file and recreates clean tables.
    Guarantees a completely fresh start."""
    import os
    db_path = str(DB_PATH)
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Recreate all tables immediately
    init_db()
    print("🗑️ FULL DATABASE WIPE COMPLETE: Everything deleted and fresh tables created.")


# ====================== SESSION MANAGEMENT ======================
def refresh_default_session() -> int:
    """Erneuert die Default-Session (z.B. nach Full Reset)."""
    global DEFAULT_SESSION_ID
    DEFAULT_SESSION_ID = get_or_create_session("default")
    return DEFAULT_SESSION_ID


# Auto-initialize
init_db()
DEFAULT_SESSION_ID = get_or_create_session("default")