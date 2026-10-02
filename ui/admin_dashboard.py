"""
SmartHelpDesk Admin Dashboard
Run:
streamlit run ui/admin_dashboard.py --server.port 8502
"""

import os
import requests
import pandas as pd
import streamlit as st

# ============================================================
# CONFIG
# ============================================================

API_BASE = os.getenv("API_URL", "http://127.0.0.1:8000")

LOGIN_URL = f"{API_BASE}/auth/login"
SUMMARY_URL = f"{API_BASE}/admin/summary"
TICKETS_URL = f"{API_BASE}/admin/tickets"
CONVERSATIONS_URL = f"{API_BASE}/admin/conversations"
DECISIONS_URL = f"{API_BASE}/admin/decisions"

st.set_page_config(
    page_title="SmartHelpDesk Admin",
    page_icon="📊",
    layout="wide"
)

# ============================================================
# AUTH GATE
# ============================================================
# /admin/* endpoints require a bearer token (see app/core/security.py),
# so this standalone dashboard needs its own lightweight login, same
# backend as the main chat UI. Admins log in with the same
# username/password created via /auth/register.
# ============================================================

if "access_token" not in st.session_state:
    st.session_state.access_token = None
    st.session_state.auth_username = None

if not st.session_state.access_token:
    st.title("📊 SmartHelpDesk Admin Dashboard")
    st.caption("Log in with your SmartHelpDesk account to view admin data.")

    with st.form("admin_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        try:
            resp = requests.post(
                LOGIN_URL,
                json={"username": username, "password": password},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            st.session_state.access_token = data["access_token"]
            st.session_state.auth_username = data["username"]
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {str(e)}")

    st.stop()


def _auth_headers():
    return {"Authorization": f"Bearer {st.session_state.access_token}"}


# ============================================================
# HELPERS
# ============================================================

def fetch_json(url):
    try:
        response = requests.get(url, headers=_auth_headers(), timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch data: {str(e)}")
        return None

# ============================================================
# HEADER
# ============================================================

with st.sidebar:
    st.caption(f"Signed in as **{st.session_state.auth_username}**")
    if st.button("Log out", use_container_width=True):
        st.session_state.access_token = None
        st.session_state.auth_username = None
        st.rerun()

st.title("📊 SmartHelpDesk Admin Dashboard")
st.caption("Internal analytics, conversations, tickets, and routing decisions.")

# ============================================================
# REFRESH BUTTON
# ============================================================

col1, col2 = st.columns([1, 6])

with col1:
    if st.button("🔄 Refresh"):
        st.rerun()

st.divider()

# ============================================================
# SUMMARY
# ============================================================

summary = fetch_json(SUMMARY_URL)

if summary:

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "🎫 Tickets",
            summary.get("tickets", 0)
        )

    with col2:
        st.metric(
            "💬 Conversations",
            summary.get("conversations", 0)
        )

    with col3:
        st.metric(
            "🧠 Decisions",
            summary.get("decisions", 0)
        )

st.divider()

# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3 = st.tabs([
    "🎫 Tickets",
    "💬 Conversations",
    "🧠 Decision Logs"
])

# ============================================================
# TICKETS
# ============================================================

with tab1:

    st.subheader("🎫 Tickets")

    tickets = fetch_json(TICKETS_URL)

    if tickets:
        df = pd.DataFrame(tickets)
        st.dataframe(
            df,
            use_container_width=True
        )

# ============================================================
# CONVERSATIONS
# ============================================================

with tab2:

    st.subheader("💬 Conversations")

    conversations = fetch_json(CONVERSATIONS_URL)

    if conversations:
        df = pd.DataFrame(conversations)
        st.dataframe(
            df,
            use_container_width=True
        )

# ============================================================
# DECISION LOGS
# ============================================================

with tab3:

    st.subheader("🧠 Routing Decisions")

    decisions = fetch_json(DECISIONS_URL)

    if decisions:
        df = pd.DataFrame(decisions)
        st.dataframe(
            df,
            use_container_width=True
        )
