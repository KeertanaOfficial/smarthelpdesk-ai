from typing import Dict, List
import os
import uuid
from datetime import datetime

from app.db.models import Ticket
from app.db.db import SessionLocal


# ============================================================
# Base Interface
# ============================================================
class TicketService:
    def create_ticket(self, payload: Dict) -> Dict:
        raise NotImplementedError

    def get_tickets_by_email(self, email: str) -> List[Dict]:
        raise NotImplementedError


# ============================================================
# DB Ticket Service (PRIMARY)
# ============================================================
class DBTicketService(TicketService):

    def create_ticket(self, payload: Dict) -> Dict:
        db = SessionLocal()
        try:
            ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"

            ticket = Ticket(
                id=ticket_id,
                email=payload.get("email"),          
                summary=payload.get("summary"),           
                description=payload.get("description"),    
                category=payload.get("category", "IT"),
                priority=payload.get("priority", "Medium"),
                status="Open",
                created_at=datetime.utcnow(),
            )

            db.add(ticket)
            db.commit()

            return {
                "ticket_id": ticket_id,
                "ticket_url": f"http://127.0.0.1:8000/admin/tickets/{ticket_id}",  
                "status": "Open"
            }

        except Exception as e:
            db.rollback()
            raise RuntimeError(f"DB ticket creation failed: {e}")

        finally:
            db.close()

    def get_tickets_by_email(self, email: str) -> List[Dict]:
        db = SessionLocal()
        try:
            tickets = db.query(Ticket).filter(Ticket.email == email).all()

            return [
                {
                    "ticket_id": t.id,
                    "email": t.email,
                    "summary": t.summary,
                    "description": t.description,
                    "category": t.category,
                    "priority": t.priority,
                    "status": t.status,
                    "ticket_url": f"http://127.0.0.1:8000/admin/tickets/{t.id}",
                    "created_at": str(t.created_at),
                }
                for t in tickets
            ]

        finally:
            db.close()


# ============================================================
# Mock fallback (safe)
# ============================================================
class MockTicketService(TicketService):

    def create_ticket(self, payload: Dict) -> Dict:
        ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"

        return {
            "ticket_id": ticket_id,
            "ticket_url": f"http://127.0.0.1/demo/{ticket_id}",
            "status": "Open"
        }

    def get_tickets_by_email(self, email: str) -> List[Dict]:
        return []


def get_ticket_service() -> TicketService:
    backend = os.getenv("TICKET_BACKEND", "db").lower()

    if backend == "db":
        return DBTicketService()

    if backend == "mock":
        return MockTicketService()

    # ✅ ALWAYS return something safe
    return DBTicketService()