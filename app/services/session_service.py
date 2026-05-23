from typing import Optional

# In-memory session store
_sessions = {}


def get_session(session_id: str):
    return _sessions.get(session_id, {
        "email": None,
        "history": [],
        "ticket_draft": {},
        "awaiting": None,
        "ticket_pending": False,
        "ticket_created": False
    })


def save_session(
    session_id: str,
    email: Optional[str],
    history: list,
    ticket_draft: dict,
    awaiting: Optional[str] = None,
):
    _sessions[session_id] = {
        "email": email,
        "history": history,
        "ticket_draft": ticket_draft,
        "awaiting": awaiting,
    }


def clear_session(session_id: str):
    if session_id in _sessions:
        del _sessions[session_id]