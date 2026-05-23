"""
SmartDesk Copilot - Streamlit Chat UI
Run:
streamlit run ui/app.py
"""

import uuid
import requests
import streamlit as st

# ============================================================
# CONFIG
# ============================================================

API_URL = "http://127.0.0.1:8000/chat"
RESET_BASE_URL = "http://127.0.0.1:8000/session"

st.set_page_config(
    page_title="SmartDesk Copilot",
    page_icon="🤖",
    layout="wide",
)

# ============================================================
# SESSION STATE
# ============================================================

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "email" not in st.session_state:
    st.session_state.email = ""

if "pending_ticket" not in st.session_state:
    st.session_state.pending_ticket = False

# ============================================================
# HELPERS
# ============================================================

def append_message(role: str, content: str):
    st.session_state.messages.append({
        "role": role,
        "content": content,
    })


def call_api(message: str):
    payload = {
        "message": message,
        "session_id": st.session_state.session_id,
        "email": st.session_state.email,
    }

    response = requests.post(
        API_URL,
        json=payload,
        timeout=120,
    )

    response.raise_for_status()

    return response.json()


def render_messages():
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def reset_conversation():
    try:
        requests.delete(
            f"{RESET_BASE_URL}/{st.session_state.session_id}",
            timeout=10,
        )
    except Exception:
        pass

    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.pending_ticket = False


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🤖 SmartDesk Copilot")
    st.caption("AI-powered Internal Helpdesk Assistant")

    st.divider()

    st.subheader("📧 Your Email")

    st.session_state.email = st.text_input(
        "",
        value=st.session_state.email,
        placeholder="you@company.com",
    )

    st.divider()

    st.subheader("🆔 Session ID")

    st.code(
        st.session_state.session_id[:12] + "...",
        language=None,
    )

    if st.button("New Conversation", use_container_width=True):
        reset_conversation()
        st.rerun()

    st.divider()

    st.markdown("### Try asking:")

    st.markdown("- VPN is not working")
    st.markdown("- Reset my password")
    st.markdown("- Create a ticket")
    st.markdown("- What is the status of my tickets?")
    st.markdown("- How many leave days do I get?")

# ============================================================
# MAIN CHAT UI
# ============================================================

st.title("💬 SmartDesk Copilot")

st.caption(
    "Ask questions about HR policies, IT support, password resets, VPN issues, or ticket status."
)

render_messages()

# ============================================================
# CHAT INPUT
# ============================================================

prompt = st.chat_input("Type your message...")

if prompt:

    append_message("user", prompt)

    with st.chat_message("user"):
        st.markdown(prompt)

    try:

        response = call_api(prompt)

        answer = response.get("answer", "")

        if not answer:
            answer = "I couldn't generate a response."

        append_message("assistant", answer)

        with st.chat_message("assistant"):
            st.markdown(answer)

    except Exception as e:

        error_msg = f"Backend error: {str(e)}"

        append_message("assistant", error_msg)

        with st.chat_message("assistant"):
            st.error(error_msg)