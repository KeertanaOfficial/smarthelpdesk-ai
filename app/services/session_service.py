"""
Session Service - Multi-turn conversation memory.
Persists conversation state per session_id in SQLite.
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional
from datetime import datetime

DB_PATH = Path("data/sessions.db")


def _init_db():
    """Create sessions table if not exists."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            email TEXT,
            history TEXT NOT NULL,
            ticket_draft TEXT,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


_init_db()


def get_session(session_id: str) -> dict:
    """Load session from DB. Returns empty dict if not found."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT email, history, ticket_draft FROM sessions WHERE session_id = ?",
        (session_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"email": None, "history": [], "ticket_draft": {}}

    email, history_json, ticket_json = row
    return {
        "email": email,
        "history": json.loads(history_json) if history_json else [],
        "ticket_draft": json.loads(ticket_json) if ticket_json else {},
    }


def save_session(
    session_id: str,
    email: Optional[str],
    history: list,
    ticket_draft: dict,
):
    """Persist session state."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO sessions (session_id, email, history, ticket_draft, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            email = excluded.email,
            history = excluded.history,
            ticket_draft = excluded.ticket_draft,
            updated_at = excluded.updated_at
    """, (
        session_id,
        email,
        json.dumps(history),
        json.dumps(ticket_draft),
        datetime.utcnow().isoformat(),
    ))
    conn.commit()
    conn.close()


def append_to_history(session_id: str, role: str, content: str):
    """Append a single message to conversation history."""
    session = get_session(session_id)
    session["history"].append({
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
    })
    # Cap history at last 20 messages to avoid context bloat
    session["history"] = session["history"][-20:]
    save_session(
        session_id,
        session["email"],
        session["history"],
        session["ticket_draft"],
    )


def clear_session(session_id: str):
    """Delete a session (useful for testing)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()