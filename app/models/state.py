from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ConversationTurn(BaseModel):
    role: str
    content: str


class RetrievedChunk(BaseModel):
    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TicketDraft(BaseModel):
    email: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = "Medium"
    confirmed: bool = False
    ticket_id: Optional[str] = None
    ticket_url: Optional[str] = None


class AgentState(BaseModel):
    user_message: str
    session_id: Optional[str] = None

    intent: Optional[str] = None
    domain: Optional[str] = None
    answer: str = ""

    retrieved_chunks: List[RetrievedChunk] = Field(default_factory=list)
    related_questions: List[str] = Field(default_factory=list)

    errors: List[str] = Field(default_factory=list)
    history: List[ConversationTurn] = Field(default_factory=list)

    session: Dict[str, Any] = Field(default_factory=dict)

    ticket: TicketDraft = Field(default_factory=TicketDraft)

    needs_escalation: bool = False
    
