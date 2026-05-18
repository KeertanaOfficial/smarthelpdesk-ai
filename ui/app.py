"""
SmartDesk AI - Streamlit Chat UI
Run: streamlit run ui/app.py
"""

import uuid
import requests
import streamlit as st


# ============================================================
# HELPERS
# ============================================================

def call_api(message: str, confirm: bool = False):
    """
    Calls backend /chat endpoint with the correct schema.
    Returns parsed JSON response.
    Raises exception if request fails.
    """
    payload = {
        "message": message,
        "session_id": st.session_state.session_id,
        "email": st.session_state.email or None,
        "confirm": confirm,
    }

    resp = requests.post(API_URL, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def append_message(role: str, content: str, extra: dict | None = None):
    """
    Append a message to the chat history with optional extra fields.
    """
    msg = {"role": role, "content": content}
    if extra:
        msg.update(extra)
    st.session_state.messages.append(msg)

# ============================================================
# CONFIG
# ============================================================

API_URL = "http://127.0.0.1:8000/chat"
RESET_BASE_URL = "http://127.0.0.1:8000/session"

st.set_page_config(
    page_title="SmartDesk AI",
    page_icon="💬",
    layout="centered",
)

# ============================================================
# SESSION STATE
# ============================================================

# ============================================================
# SESSION STATE (FIXED)
# ============================================================

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# ✅ FIX (THIS WAS MISSING)
if "email" not in st.session_state:
    st.session_state.email = "you@company.com"

if "pending_ticket" not in st.session_state:
    st.session_state.pending_ticket = False

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

def render_messages():
    """
    Render entire chat history.
    """
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # Optional: show routed label
            if msg.get("routed_to"):
                st.caption(f"Routed to: {msg['routed_to']}")

            # Optional: show ticket details
            ticket_info = msg.get("ticket_info")
            if ticket_info:
                with st.expander("Ticket Details"):
                    st.json(ticket_info)

            # Optional: show suggested questions
            suggestions = msg.get("suggested_questions", [])
            if suggestions:
                st.markdown("**Suggested Questions**")
                cols = st.columns(len(suggestions))
                for i, q in enumerate(suggestions):
                    if cols[i].button(q, key=f"suggest_{msg.get('id', i)}_{i}"):
                        st.session_state.pending_query = q
                        st.rerun()


def reset_conversation():
    """
    Reset frontend state and tell backend to clear the session.
    """
    try:
        requests.delete(f"{RESET_BASE_URL}/{st.session_state.session_id}", timeout=10)
    except Exception:
        pass

    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.pending_ticket = False
    st.session_state.pending_query = None


def normalize_routing_label(data: dict) -> str | None:
    """
    Convert backend intent/domain into a friendly label.
    """
    intent = data.get("intent", "")
    domain = data.get("domain", "")

    if intent == "kb_query" and domain == "hr":
        return "🔎 Knowledge Base (HR)"
    if intent == "kb_query" and domain == "it":
        return "🔎 Knowledge Base (IT)"
    if intent == "create_ticket":
        return "🎫 Ticket Creation"
    if intent == "check_status":
        return "📋 Ticket Status"
    return None


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.title("🤖 SmartDesk AI")
    st.caption("Your Internal Helpdesk Assistant")

    st.divider()

    email_input = st.text_input(
        "📧 Your Email",
        value=st.session_state.email,
        placeholder="you@company.com",
    )
    st.session_state.email = email_input

    st.divider()

    st.caption("Session ID:")
    st.code(st.session_state.session_id[:8] + "...", language=None)

    if st.button("New Conversation", use_container_width=True):
        reset_conversation()
        st.rerun()

    st.divider()
    st.caption("Try asking:")
    st.markdown(
        """
        - How many leave days do I get?
        - How many sick leave days are available annually?
        - What is the maternity leave policy?
        - How do I reset my password?
        - My VPN isn't working
        - Create a ticket for slow laptop
        - Status of my tickets
        """
            )

# ============================================================
# MAIN CHAT AREA
# ============================================================

st.title("💬 SmartDesk AI Chat")
st.caption("Ask me anything about HR policies, IT support, or your tickets.")

render_messages()

# ============================================================
# CONFIRM TICKET BUTTONS
# ============================================================

if st.session_state.pending_ticket:
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("✅ Confirm & Create Ticket", use_container_width=True, type="primary"):
            try:
                with st.spinner("Creating ticket..."):
                    data = call_api("Yes, please create the ticket", confirm=True)

                answer = data.get("answer", "Ticket created.")
                ticket_info = data.get("ticket")
                routed_to = normalize_routing_label(data)

                append_message(
                    "assistant",
                    answer,
                    extra={
                        "ticket_info": ticket_info if ticket_info and ticket_info.get("ticket_id") else None,
                        "routed_to": routed_to,
                        "id": str(uuid.uuid4()),
                    },
                )

                st.session_state.pending_ticket = False
                st.rerun()

            except requests.exceptions.RequestException as e:
                st.error(f"API error: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            append_message(
                "assistant",
                "Ticket creation cancelled.",
                extra={"id": str(uuid.uuid4())},
            )
            st.session_state.pending_ticket = False
            st.rerun()

# ============================================================
# AUTO-FIRE CLICKED SUGGESTED QUESTION
# ============================================================

auto_prompt = None
if st.session_state.pending_query:
    auto_prompt = st.session_state.pending_query
    st.session_state.pending_query = None

# ============================================================
# CHAT INPUT
# ============================================================

prompt = auto_prompt if auto_prompt else st.chat_input("Type your message...")

if prompt:
    append_message("user", prompt, extra={"id": str(uuid.uuid4())})

    try:
        with st.spinner("Thinking..."):
            data = call_api(prompt, confirm=False)

        # Parse response
        answer = data.get("answer", "No response returned.")
        routed_to = normalize_routing_label(data)
        ticket_info = data.get("ticket")
        suggested_questions = (
            data.get("session", {}).get("suggested_questions", [])
            if isinstance(data.get("session"), dict)
            else []
        )

        # Determine whether ticket confirmation is pending
        session_data = data.get("session", {}) if isinstance(data.get("session"), dict) else {}
        awaiting_confirmation = (
            session_data.get("awaiting_confirmation", False)
            or session_data.get("ticket_pending", False)
        )

        # Show assistant response
        append_message(
            "assistant",
            answer,
            extra={
                "ticket_info": ticket_info if ticket_info and ticket_info.get("ticket_id") else None,
                "routed_to": routed_to,
                "suggested_questions": suggested_questions,
                "id": str(uuid.uuid4()),
            },
        )

        st.session_state.pending_ticket = awaiting_confirmation
        st.rerun()

    except requests.exceptions.HTTPError as e:
        try:
            error_payload = e.response.json()
            detail = error_payload.get("detail", error_payload)
            st.error(f"API error: {e}\n\n{detail}")
        except Exception:
            st.error(f"API error: {e}")

    except requests.exceptions.RequestException as e:
        st.error(f"API error: {e}")

    except Exception as e:
        st.error(f"Unexpected error: {e}")

    st.session_state.messages = []

if "email" not in st.session_state:
    st.session_state.email = ""

if "pending_ticket" not in st.session_state:
    st.session_state.pending_ticket = False

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None