"""
LangGraph state definitions.
Uses TypedDict for the graph's internal state (LangGraph convention).
Pydantic models stay for API I/O.
"""

from typing import Optional, List, Literal, Dict, TypedDict, Annotated
from pydantic import BaseModel, Field
from operator import add

# ============================================================
# Pydantic models (API I/O — unchanged)
# ============================================================
IntentType = Literal["kb_query", "create_ticket", "check_status", "unknown"]
DomainType = Literal["hr", "it", "unknown"]
PriorityType = Literal["Low", "Medium", "High", "Critical"]


class RetrievedChunk(BaseModel):
    content: str
    source: str
    score: float
    metadata: Dict = Field(default_factory=dict)


class TicketDraft(BaseModel):
    email: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: PriorityType = "Medium"
    confirmed: bool = False
    ticket_id: Optional[str] = None
    ticket_url: Optional[str] = None


class ConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


# ============================================================
# LangGraph state (TypedDict — idiomatic LangGraph)
# ============================================================
class GraphState(TypedDict, total=False):
    """
    LangGraph internal state.
    Annotated fields with `add` accumulate across nodes (lists).
    """
    # Identity
    session_id: str
    user_message: str

    # Routing
    intent: str
    domain: str

    # Retrieval (replaced each retrieval — no `add`)
    retrieved_chunks: List[Dict]   # dict form of RetrievedChunk

    # Output
    answer: str
    needs_escalation: bool

    # Ticket flow
    ticket: Dict   # dict form of TicketDraft
    awaiting_confirmation: bool

    # Memory
    history: List[Dict]
    session: Dict

    # Diagnostics (accumulates)
    errors: Annotated[List[str], add]


# ============================================================
# AgentState (legacy Pydantic — kept for backwards compat)
# ============================================================
class AgentState(BaseModel):
    session_id: str = ""
    user_message: str = ""
    intent: IntentType = "unknown"
    domain: DomainType = "unknown"
    retrieved_chunks: List[RetrievedChunk] = Field(default_factory=list)
    answer: Optional[str] = None
    needs_escalation: bool = False
    ticket: TicketDraft = Field(default_factory=TicketDraft)
    history: List[ConversationTurn] = Field(default_factory=list)
    session: Dict = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)