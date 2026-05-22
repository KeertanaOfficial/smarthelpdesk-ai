from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
import datetime
import uuid

Base = declarative_base()


# ============================================================
# Conversations (full chat history + decisions)
# ============================================================
class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, index=True)
    user_message = Column(Text)
    assistant_response = Column(Text)

    intent = Column(String)
    domain = Column(String)

    routed_to = Column(String)    # HR/IT/Ticket
    decision = Column(String)     # "answered" / "escalated"

    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ============================================================
# Tickets (core system of record)
# ============================================================
class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String, primary_key=True)  # TKT-xxxx
    external_id = Column(String)           # Notion/Jira ID

    email = Column(String, index=True)

    summary = Column(String)
    description = Column(Text)

    category = Column(String)
    priority = Column(String)

    status = Column(String, default="Open")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ============================================================
# Decisions (super important for debugging)
# ============================================================
class DecisionLog(Base):
    __tablename__ = "decision_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    session_id = Column(String)

    step = Column(String)         # router, retrieval, guardrail
    input = Column(Text)
    output = Column(Text)

    extra_data = Column(JSON)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)