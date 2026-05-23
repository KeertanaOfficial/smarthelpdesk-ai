from app.models.state import AgentState
from app.services.ticket_service import get_ticket_service


def ticket_status_agent(state: AgentState) -> AgentState:
    email = state.session.get("email")

    if not email:
        state.answer = (
            "Please provide your email so I can look up your tickets."
        )
        return state

    svc = get_ticket_service()

    tickets = svc.get_tickets_by_email(email)

    if not tickets:
        state.answer = f"No tickets found for {email}."
        return state

    lines = []

    for t in tickets:
        summary = t.get("summary", "Support Request")

        # Prevent corrupted summaries
        if "@" in summary:
            summary = "Support Request"

        lines.append(
            f"• {t['ticket_id']} — {summary} — Status: {t['status']}"
        )

    state.answer = (
        f"I found {len(tickets)} ticket(s) for {email}:\n\n"
        + "\n\n".join(lines)
    )

    return state