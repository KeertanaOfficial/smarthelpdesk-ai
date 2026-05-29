from app.models.state import AgentState
from app.services.ticket_service import get_ticket_service


def ticket_create_agent(state: AgentState) -> AgentState:
    ticket = state.ticket

    import re

    # Extract email if present
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', state.user_message)

    clean_message = state.user_message

    # Remove email from sentence
    if email_match:
        clean_message = clean_message.replace(email_match.group(0), "")

    # Remove ticket creation filler words
    clean_message = (
        clean_message
        .replace("can you create a ticket for", "")
        .replace("create a ticket for", "")
        .replace("create ticket for", "")
        .replace("for the email", "")
        .replace("please", "")
        .strip()
    )

    # Cleanup spaces
    clean_message = " ".join(clean_message.split())

    # Fallback
    if not clean_message:
        clean_message = "VPN Issue"

    # Title / Summary
    if not ticket.summary:
        ticket.summary = clean_message

    # Description
    if not ticket.description:
        ticket.description = f"User reported issue: {clean_message}"
        
    if not ticket.category:
        ticket.category = "IT"

    if not ticket.priority:
        ticket.priority = "Medium"

    # Reuse remembered email
    if not ticket.email:
        remembered_email = state.session.get("email")

        if remembered_email:
            ticket.email = remembered_email
        else:
            state.answer = (
                "Please provide your work email address "
                "to create the ticket."
            )

            state.session["awaiting"] = "email"

            state.session["ticket_draft"] = {
                "summary": ticket.summary,
                "description": ticket.description,
                "category": ticket.category,
                "priority": ticket.priority,
            }

            return state

    # Confirmation step
    if not ticket.confirmed:
        state.answer = f"""
Please confirm your ticket details:

• Email: {ticket.email}\n
• Summary: {ticket.summary}\n
• Description: {ticket.description}\n
• Category: {ticket.category}\n
• Priority: {ticket.priority}\n

Reply with 'confirm' to create the ticket.
"""

        state.session["awaiting"] = "confirmation"

        state.session["ticket_draft"] = {
            "email": ticket.email,
            "summary": ticket.summary,
            "description": ticket.description,
            "category": ticket.category,
            "priority": ticket.priority,
        }

        return state

    # Prevent duplicate creation
    if state.session.get("ticket_created"):
        state.answer = (
            f"Ticket already created.\n\n"
            f"Ticket ID: {state.session.get('last_ticket_id')}"
        )
        return state

    # Create ticket
    try:
        svc = get_ticket_service()

        created = svc.create_ticket({
            "email": ticket.email,
            "summary": ticket.summary,
            "description": ticket.description,
            "category": ticket.category,
            "priority": ticket.priority,
        })

        ticket.ticket_id = created["ticket_id"]

        # Persist memory
        state.session["email"] = ticket.email
        state.session["ticket_created"] = True
        state.session["last_ticket_id"] = ticket.ticket_id
        state.session["awaiting"] = None

        state.answer = f"""
✅ Ticket created successfully!

• Ticket ID: {ticket.ticket_id}

• Status: {created.get("status", "Open")}

You can ask 'what is the status of my tickets?' anytime.
"""

    except Exception as e:
        state.answer = f"Failed to create ticket: {str(e)}"

    return state