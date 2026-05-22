"""
LangGraph workflow with:
- SQLite checkpointer (multi-turn persistence)
- interrupt() for human-in-loop ticket confirmation
- Defensive output guard
"""

from pathlib import Path
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt

from app.models.state import AgentState
from app.agents.router import router_agent
from app.agents.hr_agent import hr_agent
from app.agents.it_agent import it_agent
from app.agents.ticket_create_agent import ticket_create_agent
from app.agents.ticket_status_agent import ticket_status_agent

# Guardrails
from app.guardrails.input_validator import validate_input
from app.guardrails.groundedness import check_groundedness
from app.guardrails.output_sanitizer import sanitize_output
from app.guardrails.pii_redactor import extract_email


# ============================================================
# Checkpointer (SQLite-backed)
# ============================================================
CHECKPOINT_DB = Path("data/langgraph_checkpoints.db")
CHECKPOINT_DB.parent.mkdir(parents=True, exist_ok=True)

# ============================================================
# Guardrail nodes
# ============================================================
def input_guard(state: AgentState) -> AgentState:
    """Pre-router input validation."""
    result = validate_input(state.user_message)

    if not result.valid:
        state.answer = (
            f"⚠️ Your message could not be processed: {result.reason}\n"
            "Please rephrase your question about HR or IT topics."
        )
        state.intent = "unknown"
        state.errors.append(f"input_blocked: {result.reason}")
        state.session["input_blocked"] = True
        state.session["input_flags"] = result.flags
    else:
        state.session["input_blocked"] = False

    # Auto-extract email
    try:
        detected_email = extract_email(state.user_message)
        if detected_email and not state.ticket.email:
            state.ticket.email = detected_email
    except Exception as e:
        state.errors.append(f"email_extract_error: {e}")

    return state


def output_guard(state: AgentState) -> AgentState:
    if not state.answer:
        return state

    # ✅ Only run groundedness for PURE RAG answers
    is_rag_answer = (
        state.intent == "kb_query"
        and state.domain in ["hr", "it"]
        and state.retrieved_chunks
        and not state.needs_escalation
        and not (state.ticket.ticket_id and state.session.get("confidence_label") == "system_action")
        and not state.session.get("ticket_pending")
    )

    if is_rag_answer:
        try:
            gc = check_groundedness(state.answer, state.retrieved_chunks)

            if isinstance(gc, dict):
                state.session["groundedness"] = gc

                if not gc.get("grounded", True):
                    state.session["groundedness_failed"] = True

                    state.answer = (
                        "I found some information, but I'm not fully confident. "
                        "Let me suggest creating a ticket so a specialist can help.\n\n"
                        f"(Confidence: {gc.get('score', 0):.0%})"
                    )
                    state.needs_escalation = True

        except Exception as e:
            state.errors.append(f"groundedness_error: {e}")

    # ✅ Skip groundedness for ALL ticket flows
    else:
        # Optional: clear stale values
        state.session.pop("groundedness", None)

    # ✅ Always sanitize output
    try:
        result = sanitize_output(state.answer)
        if isinstance(result, tuple) and len(result) == 2:
            state.answer, flags = result
            if flags:
                state.session["output_flags"] = flags
    except Exception as e:
        state.errors.append(f"sanitize_error: {e}")

    return state

# ============================================================
# HITL Confirmation Node (NEW — uses interrupt)
# ============================================================
def human_confirmation(state: AgentState) -> AgentState:
    """
    Pauses graph execution and waits for human confirmation.
    Frontend sends back a Command(resume=...) to continue.
    """
    # Build confirmation car
    #state.ticket = state.ticket.model_dump()
    ticket = state.ticket
    state.answer = (
        f"🎫 **Please confirm ticket creation:**\n\n"
        f"• **Email:** {ticket.email}\n"
        f"• **Summary:** {ticket.summary}\n"
        f"• **Description:** {ticket.description[:200] if ticket.description else 'N/A'}...\n"
        f"• **Category:** {ticket.category}\n"
        f"• **Priority:** {ticket.priority}\n\n"
        f"Reply with **'yes'** or click ✅ to create."
    )
    state.session["awaiting_confirmation"] = True
    state.session["ticket_pending"] = True

    # interrupt() pauses execution; caller resumes via Command(resume=value)
    user_response = interrupt({
        "type": "ticket_confirmation",
        "ticket_draft": ticket.model_dump(),
        "prompt": "Confirm ticket creation?",
    })

    # Resumed — user_response is whatever the caller passed
    if isinstance(user_response, dict):
        confirmed = user_response.get("confirmed", False)
    elif isinstance(user_response, str):
        confirmed = user_response.lower() in ["yes", "confirm", "y", "ok"]
    else:
        confirmed = bool(user_response)

    state.ticket.confirmed = confirmed
    state.session["awaiting_confirmation"] = False
    return state


# ============================================================
# Routing
# ============================================================
def route_after_input_guard(state: AgentState):
    if state.session.get("input_blocked"):
        return "output_guard"
    if state.session.get("force_ticket_create"):
        return "ticket_create"
    return "router"


def route_after_router(state: AgentState):
    if state.session.get("force_ticket_create"):
        return "ticket_create"
    if state.intent == "check_status":
        return "ticket_status"
    if state.intent == "create_ticket":
        return "ticket_create"
    if state.intent == "kb_query" and state.domain == "hr":
        return "hr_agent"
    if state.intent == "kb_query" and state.domain == "it":
        return "it_agent"
    return "output_guard"


def route_after_specialist(state: AgentState):
    """
    DO NOT auto-create tickets.
    Only route to ticket_create if user explicitly confirmed.
    """
    # ✅ Only create ticket if user explicitly confirmed
    if state.session.get("user_confirmed_ticket"):
        return "ticket_create"

    # ✅ Otherwise continue normally
    return "output_guard"



def route_after_ticket_create(state: AgentState):
    """Decide if we need HITL confirmation or can finalize."""
    ticket = state.ticket
    has_all_fields = ticket.email and ticket.summary and ticket.description
    needs_confirmation = has_all_fields and not ticket.confirmed and not ticket.ticket_id

    if needs_confirmation:
        return "human_confirmation"
    return "output_guard"


def route_after_confirmation(state: AgentState):
    """After human confirms, retry ticket creation to actually submit."""
    if state.ticket.confirmed:
        return "ticket_create"
    return "output_guard"


# ============================================================
# Build graph (with optional checkpointing)
# ============================================================
def build_graph(use_checkpointer: bool = False):
    graph = StateGraph(AgentState)

    graph.add_node("input_guard", input_guard)
    graph.add_node("router", router_agent)
    graph.add_node("hr_agent", hr_agent)
    graph.add_node("it_agent", it_agent)
    graph.add_node("ticket_create", ticket_create_agent)
    graph.add_node("ticket_status", ticket_status_agent)
    graph.add_node("human_confirmation", human_confirmation)
    graph.add_node("output_guard", output_guard)

    graph.set_entry_point("input_guard")

    graph.add_conditional_edges("input_guard", route_after_input_guard, {
        "router": "router",
        "ticket_create": "ticket_create",
        "output_guard": "output_guard",
    })

    graph.add_conditional_edges("router", route_after_router, {
        "hr_agent": "hr_agent",
        "it_agent": "it_agent",
        "ticket_create": "ticket_create",
        "ticket_status": "ticket_status",
    })

    graph.add_conditional_edges("hr_agent", route_after_specialist, {
        "ticket_create": "ticket_create",
        "output_guard": "output_guard",
    })
    graph.add_conditional_edges("it_agent", route_after_specialist, {
        "ticket_create": "ticket_create",
        "output_guard": "output_guard",
    })

    # Ticket create → confirmation OR output
    graph.add_conditional_edges("ticket_create", route_after_ticket_create, {
        "human_confirmation": "human_confirmation",
        "output_guard": "output_guard",
    })

    # After confirmation → re-enter ticket_create to actually submit
    graph.add_conditional_edges("human_confirmation", route_after_confirmation, {
        "ticket_create": "ticket_create",
        "output_guard": "output_guard",
    })

    graph.add_edge("ticket_status", "output_guard")
    graph.add_edge("output_guard", END)
    return graph.compile()