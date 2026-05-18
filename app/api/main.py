from fastapi import FastAPI
from pydantic import BaseModel
from app.models.state import AgentState, ConversationTurn, TicketDraft
from app.graph.workflow import build_graph
from app.services.session_service import get_session, save_session, clear_session
from langgraph.types import Command
import traceback
import uuid
import re
from app.db.db import SessionLocal, init_db
from app.db.models import Conversation, DecisionLog, Ticket
from typing import Optional
from sqlalchemy import desc
from app.db.db import SessionLocal, init_db
from app.db.models import Ticket, Conversation, DecisionLog


app = FastAPI(title="SmartDesk AI")

# Build graph with checkpointing enabled
workflow = build_graph(use_checkpointer=True)


def save_conversation(session_id, user_msg, response):
    db = SessionLocal()
    try:
        db.add(Conversation(
            session_id=session_id,
            user_message=user_msg,
            assistant_response=response.get("answer"),
            intent=response.get("intent"),
            domain=response.get("domain"),
            routed_to=response.get("intent"),
            decision="escalated" if response.get("needs_escalation") else "answered"
        ))
        db.commit()
    finally:
        db.close()

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    email: str | None = None
    confirm: bool = False


def _to_dict(obj):
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return {}


def _extract_email(text: str | None):
    if not text:
        return None
    match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
    return match.group(0) if match else None


def _build_graph_config(session_id: str):
    """
    LangGraph-safe config shape for checkpointing/resume.
    """
    return {
        "configurable": {
            "thread_id": session_id,
            "checkpoint_ns": ""
        }
    }



@app.get("/health")
def health():
    return {"status": "ok", "service": "smartdesk-ai"}

# ============================================================
# Admin endpoints
# ============================================================

@app.get("/admin/summary")
def admin_summary():
    db = SessionLocal()
    try:
        total_tickets = db.query(Ticket).count()
        open_tickets = db.query(Ticket).filter(Ticket.status == "Open").count()
        high_priority = db.query(Ticket).filter(Ticket.priority.in_(["High", "Critical"])).count()

        total_conversations = db.query(Conversation).count()
        total_decisions = db.query(DecisionLog).count()

        return {
            "tickets": {
                "total": total_tickets,
                "open": open_tickets,
                "high_priority": high_priority,
            },
            "conversations": {
                "total": total_conversations,
            },
            "decisions": {
                "total": total_decisions,
            },
        }
    finally:
        db.close()


@app.get("/admin/tickets")
def admin_tickets(
    status: Optional[str] = None,
    category: Optional[str] = None,
    email: Optional[str] = None,
    limit: int = 100,
):
    db = SessionLocal()
    try:
        q = db.query(Ticket)

        if status:
            q = q.filter(Ticket.status == status)
        if category:
            q = q.filter(Ticket.category == category)
        if email:
            q = q.filter(Ticket.email.ilike(f"%{email}%"))

        tickets = q.order_by(desc(Ticket.created_at)).limit(limit).all()

        return [
            {
                "id": t.id,
                "external_id": getattr(t, "external_id", None),
                "email": t.email,
                "summary": t.summary,
                "description": t.description,
                "category": t.category,
                "priority": t.priority,
                "status": t.status,
                "created_at": str(t.created_at),
            }
            for t in tickets
        ]
    finally:
        db.close()

from fastapi import HTTPException
from app.db.db import SessionLocal
from app.db.models import Ticket

# ============================================================
# ✅ Get single ticket by ID (Admin Endpoint)
# ============================================================
@app.get("/admin/tickets/{ticket_id}")
def admin_ticket_detail(ticket_id: str):
    db = SessionLocal()
    try:
        t = db.query(Ticket).filter(Ticket.id == ticket_id).first()

        if not t:
            raise HTTPException(status_code=404, detail="Ticket not found")

        return {
            "id": t.id,
            "external_id": getattr(t, "external_id", None),
            "email": t.email,
            "summary": t.summary,
            "description": t.description,
            "category": t.category,
            "priority": t.priority,
            "status": t.status,
            "ticket_url": f"http://127.0.0.1:8000/admin/tickets/{t.id}",
            "created_at": str(t.created_at),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

    finally:
        db.close()

@app.get("/admin/conversations")
def admin_conversations(
    session_id: Optional[str] = None,
    intent: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 100,
):
    db = SessionLocal()
    try:
        q = db.query(Conversation)

        if session_id:
            q = q.filter(Conversation.session_id.ilike(f"%{session_id}%"))
        if intent:
            q = q.filter(Conversation.intent == intent)
        if domain:
            q = q.filter(Conversation.domain == domain)

        rows = q.order_by(desc(Conversation.created_at)).limit(limit).all()

        return [
            {
                "id": c.id,
                "session_id": c.session_id,
                "user_message": c.user_message,
                "assistant_response": c.assistant_response,
                "intent": c.intent,
                "domain": c.domain,
                "routed_to": c.routed_to,
                "decision": c.decision,
                "created_at": str(c.created_at),
            }
            for c in rows
        ]
    finally:
        db.close()


@app.get("/admin/decisions")
def admin_decisions(
    session_id: Optional[str] = None,
    step: Optional[str] = None,
    limit: int = 100,
):
    db = SessionLocal()
    try:
        q = db.query(DecisionLog)

        if session_id:
            q = q.filter(DecisionLog.session_id.ilike(f"%{session_id}%"))
        if step:
            q = q.filter(DecisionLog.step == step)

        rows = q.order_by(desc(DecisionLog.created_at)).limit(limit).all()

        return [
            {
                "id": d.id,
                "session_id": d.session_id,
                "step": d.step,
                "input": d.input,
                "output": d.output,
                "extra_data": getattr(d, "extra_data", None),
                "created_at": str(d.created_at),
            }
            for d in rows
        ]
    finally:
        db.close()


@app.post("/chat")
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    req.email = req.email or ""
    config = _build_graph_config(session_id)

    print("✅ Incoming request:", req.model_dump())

    prior = get_session(session_id)

    try:
        # ---------------------------------------------------
        # SAFE checkpoint lookup
        # ---------------------------------------------------
        state_snapshot = None
        is_resuming = False

        try:
            state_snapshot = workflow.get_state(config)
            is_resuming = bool(state_snapshot and getattr(state_snapshot, "next", None))
        except Exception as e:
            # First run or checkpoint read issue → treat as fresh invocation
            print(f"[main] get_state skipped: {e}")
            state_snapshot = None
            is_resuming = False

        # ---------------------------------------------------
        # RESUME path (human-in-the-loop confirmation)
        # ---------------------------------------------------
        if is_resuming:
            if req.confirm:
                result = workflow.invoke(
                    Command(resume={"confirmed": True}),
                    config=config,
                )
            else:
                # If user did not confirm, resume with rejection
                result = workflow.invoke(
                    Command(resume={"confirmed": False}),
                    config=config,
                )

        # ---------------------------------------------------
        # FRESH invocation
        # ---------------------------------------------------
        else:
            state = AgentState(
                session_id=session_id,
                user_message=req.message,
            )

            extracted_email = _extract_email(req.message)

            # Restore email priority
            if req.email:
                state.ticket.email = req.email
            elif extracted_email:
                state.ticket.email = extracted_email
            elif prior.get("email"):
                state.ticket.email = prior["email"]

            # Restore draft if available
            if prior.get("ticket_draft"):
                try:
                    draft = prior["ticket_draft"]
                    # Only restore draft if confirmation is pending
                    if prior.get("awaiting_confirmation"):
                        state.ticket = TicketDraft(**prior.get("ticket_draft", {}))
                    else:
                        # NEW QUERY → reset ticket
                        state.ticket = TicketDraft()

                        # Re-apply freshest email
                        if req.email:
                            state.ticket.email = req.email
                        elif extracted_email:
                            state.ticket.email = extracted_email
                except Exception as e:
                    print(f"[main] restore ticket draft failed: {e}")

            # Apply explicit confirmation
            if req.confirm:
                state.ticket.confirmed = True

            # Restore history
            state.history = [
                ConversationTurn(**t) for t in prior.get("history", [])
            ]

            result = workflow.invoke(state, config=config)

        result_dict = _to_dict(result)

        # ---------------------------------------------------
        # Check if graph is paused awaiting confirmation
        # ---------------------------------------------------
        try:
            state_after = workflow.get_state(config)
            if state_after and getattr(state_after, "next", None):
                result_dict.setdefault("session", {})
                result_dict["session"]["awaiting_confirmation"] = True
                result_dict["session"]["ticket_pending"] = True
                result_dict["suggested_questions"] = result_dict.get("session", {}).get("suggested_questions", [])
        except Exception as e:
            print(f"[main] post-invoke get_state skipped: {e}")

        # ---------------------------------------------------
        # Persist session state
        # ---------------------------------------------------
        ticket_obj = result_dict.get("ticket")
        ticket_data = _to_dict(ticket_obj) or {}

        saved_email = (
            ticket_data.get("email")
            or req.email
            or prior.get("email")
        )

        history = prior.get("history", [])
        history.append({"role": "user", "content": req.message})
        history.append({"role": "assistant", "content": result_dict.get("answer", "")})
        history = history[-20:]

        draft_to_save = ticket_data if ticket_data and not ticket_data.get("ticket_id") else {}

        save_session(
            session_id=session_id,
            email=saved_email,
            history=history,
            ticket_draft=draft_to_save,
        )

        result_dict["session_id"] = session_id
        return result_dict

    except Exception as e:
        traceback.print_exc()
        return {
            "error": str(e),
            "type": type(e).__name__,
            "session_id": session_id,
        }


@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/admin/tickets")
def get_all_tickets():
    db = SessionLocal()
    try:
        return db.query(Ticket).all()
    finally:
        db.close()

@app.delete("/session/{session_id}")
def reset(session_id: str):
    clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}