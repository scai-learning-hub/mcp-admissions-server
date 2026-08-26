"""Admissions — MCP Chat Hub

Two pages: Learner Assistant + Counsellor Console.

Run:
  streamlit run ui/app.py --server.port 8501
"""

import requests
import streamlit as st

st.set_page_config(page_title="School of Core AI — MCP Server", page_icon="🎓", layout="wide")

LEARNER_URL = "http://localhost:8020"
COUNSELLOR_URL = "http://localhost:8030"
MCP_URL = "http://localhost:8010"


# ── Helpers ──────────────────────────────────────────────────────────────────

def chat_with_host(url: str, message: str, thread_id: str | None = None) -> dict:
    payload = {"message": message}
    if thread_id:
        payload["thread_id"] = thread_id
    try:
        resp = requests.post(f"{url}/chat", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"reply": f"⚠️ Server not running on {url}", "thread_id": "", "state": {}}
    except Exception as e:
        return {"reply": f"⚠️ {e}", "thread_id": "", "state": {}}


def confirm_with_host(url: str, thread_id: str, confirm: bool) -> dict:
    try:
        resp = requests.post(f"{url}/confirm", json={"thread_id": thread_id, "confirm": confirm}, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"reply": f"⚠️ {e}", "thread_id": "", "state": {}}


def check_health(url: str) -> bool:
    try:
        return requests.get(f"{url}/health", timeout=5).status_code == 200
    except Exception:
        return False


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("School of Core AI")
    st.caption("MCP-powered chat hub")
    st.metric("MCP Server", "✅ Online" if check_health(MCP_URL) else "❌ Offline")
    st.metric("Learner Host", "✅ Online" if check_health(LEARNER_URL) else "❌ Offline")
    st.metric("Counsellor Host", "✅ Online" if check_health(COUNSELLOR_URL) else "❌ Offline")


# ── Chat component ───────────────────────────────────────────────────────────

def render_chat(
    label: str,
    caption: str,
    placeholder: str,
    base_url: str,
    state_prefix: str,
):
    """Interactive chat with confirmation gate + verified-data expander."""

    msgs_key = f"{state_prefix}_messages"
    tid_key = f"{state_prefix}_thread_id"
    confirm_key = f"{state_prefix}_pending_confirm"

    if msgs_key not in st.session_state:
        st.session_state[msgs_key] = []
    if tid_key not in st.session_state:
        st.session_state[tid_key] = None
    if confirm_key not in st.session_state:
        st.session_state[confirm_key] = False

    st.header(label)
    st.caption(caption)

    # Chat history
    for msg in st.session_state[msgs_key]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Confirmation gate
    if st.session_state[confirm_key]:
        st.info("🔔 Action prepared. Confirm to proceed.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Confirm", key=f"{state_prefix}_yes"):
                result = confirm_with_host(base_url, st.session_state[tid_key], True)
                st.session_state[msgs_key].append({"role": "user", "content": "✅ Confirm"})
                st.session_state[msgs_key].append({"role": "assistant", "content": result.get("reply", "")})
                st.session_state[confirm_key] = False
                st.rerun()
        with c2:
            if st.button("❌ Cancel", key=f"{state_prefix}_no"):
                result = confirm_with_host(base_url, st.session_state[tid_key], False)
                st.session_state[msgs_key].append({"role": "user", "content": "❌ Cancel"})
                st.session_state[msgs_key].append({"role": "assistant", "content": result.get("reply", "")})
                st.session_state[confirm_key] = False
                st.rerun()

    # Chat input
    if prompt := st.chat_input(placeholder, key=f"{state_prefix}_input"):
        st.session_state[msgs_key].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = chat_with_host(base_url, prompt, st.session_state[tid_key])
            reply = result.get("reply", "(no reply)")
            st.session_state[tid_key] = result.get("thread_id", st.session_state[tid_key])
            st.session_state[msgs_key].append({"role": "assistant", "content": reply})
            st.write(reply)

            # Verified tool data
            state = result.get("state", {})
            facts = state.get("facts", {})
            if any(facts.get(k) for k in ("courses", "batches", "quote", "course_detail", "policy")):
                with st.expander("📋 Verified data from MCP tools"):
                    if facts.get("courses") and not facts.get("course_title"):
                        for c in facts["courses"]:
                            st.markdown(f"- **{c['title']}** ({c['level']}, {c['duration_weeks']}w) — `{c['slug']}`")
                    if facts.get("course_title"):
                        st.markdown(f"**Course:** {facts['course_title']}")
                    if facts.get("batches"):
                        for b in facts["batches"]:
                            seats = b.get("seats", {})
                            st.markdown(f"- {b.get('start_at','')} | {b.get('mode','')} | {seats.get('seats_available','?')} seats")
                    if facts.get("quote"):
                        q = facts["quote"]
                        st.markdown(f"**Fee:** {q.get('currency','')} {q.get('total','')} — `{q.get('quote_id','')[:12]}...`")
                    if facts.get("policy"):
                        p = facts["policy"]
                        st.markdown(f"**Policy:** {p.get('title','')} (v{p.get('version','')})")

            # Trigger confirmation gate
            if state.get("pending_action_preview") or state.get("pending_action") == "update_stage":
                st.session_state[confirm_key] = True
                st.rerun()

    if st.button("🗑️ Clear chat", key=f"{state_prefix}_clear"):
        st.session_state[msgs_key] = []
        st.session_state[tid_key] = None
        st.session_state[confirm_key] = False
        st.rerun()


# ── Pages ────────────────────────────────────────────────────────────────────

learner_tab, counsellor_tab = st.tabs(["🎓 Learner Assistant", "🎧 Counsellor Console"])

with learner_tab:
    render_chat(
        label="🎓 Learner Assistant",
        caption="Search courses, get fee quotes, request callbacks — powered by MCP tools",
        placeholder="Ask about courses, batches, fees, or request a callback...",
        base_url=LEARNER_URL,
        state_prefix="learner",
    )

with counsellor_tab:
    render_chat(
        label="🎧 Counsellor Console",
        caption="Search courses, check batches, get fee quotes, list leads, update stages",
        placeholder="Search courses, check batches, get fee quotes, list leads, update stages...",
        base_url=COUNSELLOR_URL,
        state_prefix="counsellor",
    )