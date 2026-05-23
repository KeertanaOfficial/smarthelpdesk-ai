"""
SmartDesk Admin Dashboard
Run:
streamlit run ui/admin_dashboard.py --server.port 8502
"""

import requests
import pandas as pd
import streamlit as st

# ============================================================
# CONFIG
# ============================================================

API_BASE = "http://127.0.0.1:8000"

SUMMARY_URL = f"{API_BASE}/admin/summary"
TICKETS_URL = f"{API_BASE}/admin/tickets"
CONVERSATIONS_URL = f"{API_BASE}/admin/conversations"
DECISIONS_URL = f"{API_BASE}/admin/decisions"

st.set_page_config(
    page_title="SmartDesk Admin",
    page_icon="📊",
    layout="wide"
)

# ============================================================
# HELPERS
# ============================================================

def fetch_json(url):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch data: {str(e)}")
        return None

# ============================================================
# HEADER
# ============================================================

st.title("📊 SmartDesk Admin Dashboard")
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