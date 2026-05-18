from app.models.state import AgentState
from app.services.ticket_service import get_ticket_service


def ticket_status_agent(state: AgentState) -> AgentState:
    # Try ticket email first, then session
    email = state.ticket.email or state.session.get("email")

    if not email:
        state.answer = "Please provide your email so I can look up your tickets."
        return state

    svc = get_ticket_service()
    tickets = svc.get_tickets_by_email(email)

    if not tickets:
        state.answer = f"I could not find any tickets for {email}."
        return state

    if len(tickets) == 1:
        t = tickets[0]
        state.answer = (
            f"I found 1 ticket for you:\n"
            f"• {t['ticket_id']} — {t['summary']}\n"
            f"  Status: {t['status']}\n"
            f"  Category: {t.get('category', 'N/A')}"
        )
        return state

    lines = [
        f"• {t['ticket_id']} — {t['summary']} — Status: {t['status']}"
        for t in tickets
    ]
    state.answer = f"I found {len(tickets)} tickets for {email}:\n" + "\n".join(lines)
    return state