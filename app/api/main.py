from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import traceback
import uuid

from app.graph.workflow import build_graph

from app.models.state import (
    AgentState,
    TicketDraft,
)

from app.services.session_service import (
    get_session,
    save_session,
    clear_session,
)

from app.agents.ticket_create_agent import (
    ticket_create_agent,
)

from app.db.db import SessionLocal
from app.db.models import (
    Ticket,
    Conversation,
    DecisionLog,
)

# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    title="SmartHelpDesk AI",
    version="1.0.0",
)

# ============================================================
# Build LangGraph Workflow
# ============================================================

workflow = build_graph(use_checkpointer=True)

# ============================================================
# Request Model
# ============================================================


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    email: Optional[str] = None
    confirm: bool = False


# ============================================================
# Helper Functions
# ============================================================


def _to_dict(obj):

    if isinstance(obj, dict):
        return obj

    if hasattr(obj, "model_dump"):
        return obj.model_dump()

    return {}


def _build_graph_config(session_id: str):

    return {
        "configurable": {
            "thread_id": session_id,
            "checkpoint_ns": "",
        }
    }


# ============================================================
# Health Endpoint
# ============================================================


@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "smarthelpdesk-ai",
    }


# ============================================================
# Reset Session
# ============================================================


@app.delete("/session/{session_id}")
def reset_session(session_id: str):

    clear_session(session_id)

    return {
        "status": "cleared",
        "session_id": session_id,
    }


# ============================================================
# Main Chat Endpoint
# ============================================================


@app.post("/chat")
def chat(req: ChatRequest):

    try:

        # ====================================================
        # Session Setup
        # ====================================================

        session_id = req.session_id or str(uuid.uuid4())

        session_data = get_session(session_id)

        # Persist sidebar email into memory
        if req.email:
            session_data["email"] = req.email

        awaiting = session_data.get("awaiting")

        config = _build_graph_config(session_id)

        print("\n================================================")
        print("Incoming Request")
        print(req.dict())
        print("Loaded Session")
        print(session_data)
        print("================================================\n")

        result = None

        # ====================================================
        # FLOW 1: Waiting For Email
        # ====================================================

        if awaiting == "email":

            draft = session_data.get("ticket_draft", {})

            ticket = TicketDraft(
                email=req.message.strip(),
                summary=draft.get("summary"),
                description=draft.get("description"),
                category=draft.get("category", "IT"),
                priority=draft.get("priority", "Medium"),
                confirmed=False,
            )

            state = AgentState(
                user_message=req.message,
                session_id=session_id,
                session=session_data,
                intent="create_ticket",
                domain="it",
                ticket=ticket,
            )

            result = ticket_create_agent(state)

        # ====================================================
        # FLOW 2: Waiting For Confirmation
        # ====================================================

        elif awaiting == "confirmation":

            draft = session_data.get("ticket_draft", {})

            ticket = TicketDraft(
                email=draft.get("email"),
                summary=draft.get("summary"),
                description=draft.get("description"),
                category=draft.get("category", "IT"),
                priority=draft.get("priority", "Medium"),
                confirmed=(
                    req.confirm
                    or req.message.lower().strip()
                    in ["confirm", "yes", "y"]
                ),
            )

            state = AgentState(
                user_message=req.message,
                session_id=session_id,
                session=session_data,
                intent="create_ticket",
                domain="it",
                ticket=ticket,
            )

            result = ticket_create_agent(state)

        # ====================================================
        # FLOW 3: Standard Workflow
        # ====================================================

        else:

            state = AgentState(
                user_message=req.message,
                session_id=session_id,
                session=session_data,
            )

            result = workflow.invoke(
                state,
                config=config,
            )

        # ====================================================
        # Convert Result
        # ====================================================

        result_dict = _to_dict(result)

        print("\n================================================")
        print("WORKFLOW RESULT")
        print(result_dict)
        print("================================================\n")

        # ====================================================
        # Save Session
        # ====================================================

        session_payload = result_dict.get("session", {})

        save_session(
            session_id=session_id,
            email=session_payload.get("email"),
            history=session_payload.get("history", []),
            ticket_draft=session_payload.get(
                "ticket_draft",
                {},
            ),
            awaiting=session_payload.get("awaiting"),
        )

        # ====================================================
        # Return API Response
        # ====================================================

        return {
            "answer": result_dict.get("answer", ""),
            "intent": result_dict.get("intent"),
            "domain": result_dict.get("domain"),
            "session_id": session_id,
            "related_questions": result_dict.get(
                "related_questions",
                [],
            ),
        }

    except Exception as e:

        traceback.print_exc()

        return {
            "answer": "",
            "error": str(e),
            "session_id": req.session_id,
        }
    
# ============================================================
# ADMIN APIs
# ============================================================
# ============================================================
# ADMIN APIs
# ============================================================

from app.db.db import SessionLocal
from app.db.models import Ticket, Conversation, DecisionLog


@app.get("/admin/summary")
def admin_summary():
    db = SessionLocal()

    try:
        return {
            "tickets": db.query(Ticket).count(),
            "conversations": db.query(Conversation).count(),
            "decisions": db.query(DecisionLog).count(),
        }

    finally:
        db.close()


@app.get("/admin/tickets")
def admin_tickets():
    db = SessionLocal()

    try:
        tickets = db.query(Ticket).all()

        results = []

        for t in tickets:
            results.append({
                "id": getattr(t, "id", None),
                "ticket_id": getattr(t, "ticket_id", None),
                "email": getattr(t, "email", None),
                "summary": getattr(t, "summary", None),
                "description": getattr(t, "description", None),
                "category": getattr(t, "category", None),
                "priority": getattr(t, "priority", None),
                "status": getattr(t, "status", None),
                "created_at": str(getattr(t, "created_at", "")),
            })

        return results

    finally:
        db.close()


@app.get("/admin/conversations")
def admin_conversations():
    db = SessionLocal()

    try:
        conversations = db.query(Conversation).all()

        results = []

        for c in conversations:
            results.append({
                "id": getattr(c, "id", None),
                "session_id": getattr(c, "session_id", None),
                "user_message": getattr(c, "user_message", None),
                "assistant_response": getattr(c, "assistant_response", None),
                "intent": getattr(c, "intent", None),
                "domain": getattr(c, "domain", None),
                "created_at": str(getattr(c, "created_at", "")),
            })

        return results

    finally:
        db.close()


@app.get("/admin/decisions")
def admin_decisions():
    db = SessionLocal()

    try:
        decisions = db.query(DecisionLog).all()

        results = []

        for d in decisions:
            results.append({
                "id": getattr(d, "id", None),
                "session_id": getattr(d, "session_id", None),
                "step": getattr(d, "step", None),
                "input": getattr(d, "input", None),
                "output": getattr(d, "output", None),
                "extra_data": getattr(d, "extra_data", None),
                "created_at": str(getattr(d, "created_at", "")),
            })

        return results

    finally:
        db.close()