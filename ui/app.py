"""
SmartHelpDesk Copilot - Streamlit Chat UI

Run:
python -m streamlit run ui/app.py
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
    page_title="SmartHelpDesk Copilot",
    page_icon="💬",
    layout="wide",
)

# Optional styling so the page feels cleaner
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 6rem;
        }

        section[data-testid="stSidebar"] {
            min-width: 360px !important;
            max-width: 420px !important;
        }

        .suggestion-header {
            font-size: 1.05rem;
            font-weight: 600;
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
        }

        .quick-actions-header {
            font-size: 1rem;
            font-weight: 600;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
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

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

# ============================================================
# SUGGESTED QUESTIONS
# ============================================================

SUGGESTIONS = {
    "🍃 Leave": [
        "How many paid leave days do employees get per year?",
        "How do I apply for sick leave?",
    ],
    "💰 Payroll": [
        "When is salary credited each month?",
        "How do I submit tax declarations?",
        "How do I download my payslip?",
        "How do I update bank account information?",
    ],
    "🧾 Reimbursement": [
        "What expenses are eligible for reimbursement?",
    ],
    "🏥 Benefits": [
        "What health insurance benefits are provided?",
        "What is the 401(k) matching policy?",
    ],
    "🙋 Onboarding": [
        "What should I do on my first day?",
        "When will I receive my laptop?",
        "How do I activate my employee ID badge?",
    ],
    "📈 Performance": [
        "How does the annual performance review work?",
        "How are bonuses calculated?",
    ],
    "🔐 IT Support": [
        "How do I reset my password?",
        "What should I do if my account gets locked?",
        "How do I set up VPN access?",
        "My VPN is not working",
        "How do I set up MFA?",
        "How do I configure company email on my mobile device?",
        "Which software applications are pre-approved?",
        "How do I request a new laptop?",
        "How do I connect to corporate Wi-Fi?",
        "How do I raise an IT support ticket?",
    ],
}

# ============================================================
# HELPERS
# ============================================================

def append_message(role: str, content: str):
    st.session_state.messages.append(
        {
            "role": role,
            "content": content,
        }
    )


def call_api(message: str):
    payload = {
        "message": message,
        "session_id": st.session_state.session_id,
        "email": st.session_state.email,
    }

    resp = requests.post(API_URL, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


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
        # Ignore backend reset failures and still clear frontend state
        pass

    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.pending_query = None


def trigger_prompt(prompt_text: str):
    st.session_state.pending_query = prompt_text
    st.rerun()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.subheader("Start a new conversation:")
    if st.button("New Conversation", use_container_width=True):
        reset_conversation()
        st.rerun()

    st.divider()

    st.subheader("Your Email")
    st.session_state.email = st.text_input(
        "Used for ticket creation and status lookup",
        value=st.session_state.email,
        placeholder="you@company.com",
    )
    if st.button("Submit", use_container_width=True):
        if not st.session_state.email:
            st.warning("Please enter your email before submitting.")

    st.divider()

    st.subheader("Try asking:")
    st.markdown('<div class="suggestion-header">💡 Suggested Questions</div>', unsafe_allow_html=True)

    for category, questions in SUGGESTIONS.items():
        with st.expander(category, expanded=False):
            for q in questions:
                if st.button(q, key=f"btn_{category}_{q}", use_container_width=True):
                    trigger_prompt(q)

    st.divider()

    st.markdown('<div class="quick-actions-header">⚡ Quick Actions</div>', unsafe_allow_html=True)
    qa_col1, qa_col2 = st.columns(2)

    with qa_col1:
        if st.button("🔑 Reset Password", use_container_width=True):
            trigger_prompt("How do I reset my password?")

    with qa_col2:
        if st.button("🎫 Create Ticket", use_container_width=True):
            trigger_prompt("I need to create a support ticket.")

 

# ============================================================
# MAIN CHAT UI
# ============================================================

st.title("💬 SmartHelpDesk Copilot")
st.caption(
    "Ask questions about HR policies, IT support, password resets, VPN issues, or ticket status."
)

render_messages()

# ============================================================
# CHAT INPUT
# ============================================================

# Keep chat input ALWAYS visible.
manual_prompt = st.chat_input("Type your message...")

# If a sidebar prompt was clicked, use that first.
selected_prompt = st.session_state.pending_query

prompt = selected_prompt if selected_prompt else manual_prompt

# Once consumed, clear pending query so the user can keep typing manually.
if selected_prompt:
    st.session_state.pending_query = None

if prompt:
    append_message("user", prompt)

    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        response = call_api(prompt)
        answer = response.get("answer", "").strip()

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
