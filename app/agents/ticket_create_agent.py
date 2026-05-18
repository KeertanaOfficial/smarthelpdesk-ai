from app.models.state import AgentState
from app.services.ticket_service import get_ticket_service


def ticket_create_agent(state: AgentState) -> AgentState:
    ticket = state.ticket

    # Auto-fill missing fields
    if not ticket.summary:
        # Take first 80 chars of message as summary
        ticket.summary = state.user_message[:80] if state.user_message else "Support request"

    if not ticket.description:
        ticket.description = state.user_message or "No description provided"

    if not ticket.category:
        ticket.category = state.domain.upper() if state.domain != "unknown" else "GENERAL"

    # Step 1: Need email
    if not ticket.email:
        state.answer = (
            "📧 To create a ticket, I need your email address. "
            "Please reply with your work email (e.g., yourname@company.com)."
        )
        # Signal UI: waiting for email
        state.session["awaiting"] = "email"
        return state

    # Step 2: Need confirmation
    if not ticket.confirmed:
        state.answer = (
            "📝 **Please confirm your ticket details:**\n\n"
            f"• **Email:** {ticket.email}\n"
            f"• **Summary:** {ticket.summary}\n"
            f"• **Description:** {ticket.description}\n"
            f"• **Category:** {ticket.category}\n"
            f"• **Priority:** {ticket.priority or 'Medium'}\n\n"
            "Reply with **'confirm'** or click the Confirm button to create the ticket."
        )
        # ✅ Explicit signal for UI
        state.session["awaiting"] = "confirmation"
        state.session["ticket_pending"] = True
        return state

    # Step 3: Create ticket
    try:
        svc = get_ticket_service()
        
        if not svc:
            state.answer = "Ticket system unavailable. Please try again."
            return state

        created = svc.create_ticket({
            "email": ticket.email,
            "summary": ticket.summary,
            "description": ticket.description,
            "category": ticket.category,
            "priority": ticket.priority or "Medium",
        })

        ticket.ticket_id = created["ticket_id"]
        ticket.ticket_url = created["ticket_url"]

        state.answer = (
            "✅ **Ticket created successfully!**\n\n"
            f"• **Ticket ID:** `{ticket.ticket_id}`\n\n"
            f"• **Status:** {created.get('status', 'Open')}\n\n"
            "You can ask 'what is the status of my tickets?' anytime."
        )
        state.session["awaiting"] = None
        state.session["ticket_pending"] = False
        state.session["ticket_created"] = True

    except Exception as e:
        state.answer = f"⚠️ Failed to create ticket: {str(e)}. Please try again or contact IT support."
        state.errors.append(f"ticket_create_failed: {e}")

    return state