import os
import requests
import pandas as pd
import streamlit as st

# ============================================================
# Config
# ============================================================
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = os.getenv("API_PORT", "8000")
APP_ENV = os.getenv("APP_ENV", "dev")

if APP_ENV == "prod":
    API_BASE = f"http://{API_HOST}"
else:
    API_BASE = f"http://{API_HOST}:{API_PORT}"

SUMMARY_URL = f"{API_BASE}/admin/summary"
TICKETS_URL = f"{API_BASE}/admin/tickets"
CONVERSATIONS_URL = f"{API_BASE}/admin/conversations"
DECISIONS_URL = f"{API_BASE}/admin/decisions"

st.set_page_config(page_title="SmartDesk Admin", page_icon="📊", layout="wide")
st.title("📊 SmartDesk Admin Dashboard")
st.caption("Tickets • Conversations • Decision Logs")

# ============================================================
# Helpers
# ============================================================
def fetch_json(url, params=None):
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Failed to fetch {url}: {e}")
        return None


def show_metric_cards(summary):
    tickets = summary.get("tickets", {})
    conversations = summary.get("conversations", {})
    decisions = summary.get("decisions", {})

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Total Tickets", tickets.get("total", 0))
    c2.metric("Open Tickets", tickets.get("open", 0))
    c3.metric("High/Critical", tickets.get("high_priority", 0))
    c4.metric("Conversations", conversations.get("total", 0))
    c5.metric("Decision Logs", decisions.get("total", 0))


# ============================================================
# Refresh button
# ============================================================
col_refresh, col_space = st.columns([1, 5])
with col_refresh:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

# ============================================================
# Summary
# ============================================================
summary = fetch_json(SUMMARY_URL)
if summary:
    show_metric_cards(summary)

st.divider()

# ============================================================
# Tabs
# ============================================================
tab1, tab2, tab3 = st.tabs(["🎫 Tickets", "💬 Conversations", "🧠 Decision Logs"])

# ============================================================
# Tickets tab
# ============================================================
with tab1:
    st.subheader("🎫 Tickets")

    f1, f2, f3, f4 = st.columns([1, 1, 2, 1])

    with f1:
        status_filter = st.selectbox(
            "Status",
            ["", "Open", "In Progress", "Resolved"],
            index=0,
        )
    with f2:
        category_filter = st.selectbox(
            "Category",
            ["", "IT", "HR"],
            index=0,
        )
    with f3:
        email_filter = st.text_input("Email contains", "")
    with f4:
        ticket_limit = st.number_input("Limit", min_value=10, max_value=500, value=100, step=10)

    ticket_params = {
        "status": status_filter or None,
        "category": category_filter or None,
        "email": email_filter or None,
        "limit": ticket_limit,
    }

    tickets = fetch_json(TICKETS_URL, params=ticket_params)

    if tickets is None:
        st.stop()

    if not tickets:
        st.info("No tickets found.")
    else:
        df = pd.DataFrame(tickets)

        display_cols = [c for c in ["id", "email", "summary", "category", "priority", "status", "created_at"] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

        st.markdown("### Ticket Details")
        for t in tickets[:25]:
            with st.expander(f"{t['id']} — {t['summary']}"):
                st.markdown(f"**Email:** {t.get('email', '')}")
                st.markdown(f"**Category:** {t.get('category', '')}")
                st.markdown(f"**Priority:** {t.get('priority', '')}")
                st.markdown(f"**Status:** {t.get('status', '')}")
                st.markdown(f"**Created:** {t.get('created_at', '')}")
                st.markdown("**Description:**")
                st.code(t.get("description", ""), language=None)

# ============================================================
# Conversations tab
# ============================================================
with tab2:
    st.subheader("💬 Conversations")

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])

    with c1:
        session_filter = st.text_input("Session ID contains", "")
    with c2:
        intent_filter = st.selectbox(
            "Intent",
            ["", "kb_query", "create_ticket", "check_status", "unknown"],
            index=0,
        )
    with c3:
        domain_filter = st.selectbox(
            "Domain",
            ["", "hr", "it", "unknown"],
            index=0,
        )
    with c4:
        conv_limit = st.number_input("Limit ", min_value=10, max_value=500, value=100, step=10)

    conv_params = {
        "session_id": session_filter or None,
        "intent": intent_filter or None,
        "domain": domain_filter or None,
        "limit": conv_limit,
    }

    conversations = fetch_json(CONVERSATIONS_URL, params=conv_params)

    if conversations is None:
        st.stop()

    if not conversations:
        st.info("No conversations found.")
    else:
        df = pd.DataFrame(conversations)
        display_cols = [c for c in ["session_id", "intent", "domain", "routed_to", "decision", "created_at"] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

        st.markdown("### Conversation Details")
        for c in conversations[:25]:
            title = f"{c.get('session_id', '')} — {c.get('intent', '')} / {c.get('domain', '')}"
            with st.expander(title):
                st.markdown(f"**Routed To:** {c.get('routed_to', '')}")
                st.markdown(f"**Decision:** {c.get('decision', '')}")
                st.markdown(f"**Created:** {c.get('created_at', '')}")
                st.markdown("**User Message:**")
                st.code(c.get("user_message", ""), language=None)
                st.markdown("**Assistant Response:**")
                st.code(c.get("assistant_response", ""), language=None)

# ============================================================
# Decisions tab
# ============================================================
with tab3:
    st.subheader("🧠 Decision Logs")

    d1, d2, d3 = st.columns([2, 1, 1])

    with d1:
        decision_session_filter = st.text_input("Session ID contains ", "")
    with d2:
        step_filter = st.text_input("Step equals", "")
    with d3:
        decision_limit = st.number_input("Limit  ", min_value=10, max_value=500, value=100, step=10)

    decision_params = {
        "session_id": decision_session_filter or None,
        "step": step_filter or None,
        "limit": decision_limit,
    }

    decisions = fetch_json(DECISIONS_URL, params=decision_params)

    if decisions is None:
        st.stop()

    if not decisions:
        st.info("No decision logs found.")
    else:
        df = pd.DataFrame(decisions)
        display_cols = [c for c in ["session_id", "step", "created_at"] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

        st.markdown("### Decision Details")
        for d in decisions[:25]:
            title = f"{d.get('session_id', '')} — {d.get('step', '')}"
            with st.expander(title):
                st.markdown(f"**Created:** {d.get('created_at', '')}")

                st.markdown("**Input:**")
                st.code(d.get("input", ""), language=None)

                st.markdown("**Output:**")
                st.code(d.get("output", ""), language=None)

                extra_data = d.get("extra_data")
                if extra_data:
                    st.markdown("**Extra Data:**")
                    st.json(extra_data)
