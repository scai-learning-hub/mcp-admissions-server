"""Admissions — NO-MCP Demo (Direct DB)

This is a SINGLE self-contained Streamlit script that does EXACTLY what the
learner host does — same LangGraph flow, same prompts, same LLM — but WITHOUT
the MCP protocol. It connects directly to PostgreSQL.

Run:
  streamlit run ui/no_mcp_demo.py --server.port 8502

Purpose: Show learners what MCP actually buys you. Compare this tab-by-tab
with the MCP-based UI at http://localhost:8501.

What's missing vs the MCP version:
  - No auth / RBAC (anyone can call anything)
  - No audit trail (who called what, when, what result)
  - No idempotency / optimistic concurrency
  - No typed tool contracts (Pydantic validation)
  - No confirmation gate (writes happen immediately)
  - No protocol versioning or discoverability
  - DB credentials are in the client process
  - Business logic is duplicated in every client
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# ─────────────────────────────────────────────────────────────────────────────
# Config — DB credentials directly in the client (BAD! MCP avoids this)
# ─────────────────────────────────────────────────────────────────────────────

DB_URL = "postgresql+psycopg://scai:scai@localhost:5433/scai_admissions"

# LLM config (same as the MCP version)
LLM_PROVIDER = "ollama"
LLM_MODEL = "qwen3.5:2b"
LLM_BASE_URL = "http://localhost:11434/v1"

engine = create_engine(DB_URL, echo=False)

# ─────────────────────────────────────────────────────────────────────────────
# LLM adapter (identical to packages/shared/llm.py)
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
from openai import AsyncOpenAI

_llm_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key="ollama")


async def llm_chat_simple(system: str, user_msg: str) -> str:
    try:
        resp = await _llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"(LLM error: {e})"


# ─────────────────────────────────────────────────────────────────────────────
# Prompts — IDENTICAL to the MCP learner host
# ─────────────────────────────────────────────────────────────────────────────

NORMALIZE_PROMPT = """\
You are the intent extraction layer for an admissions assistant.
Extract structured information from the user's message. Do NOT invent facts.

Return ONLY a JSON object with these fields (omit fields you can't determine):
{
  "intent": "enquiry" | "callback_request" | "enroll" | "policy",
  "requested_course": "agentic-ai" | "aiops" | "mlops" | "gen-ai" | null,
  "requested_mode": "online" | "in_person" | "hybrid" | null,
  "timezone": "string like Asia/Kolkata or UTC"
}

Rules:
- "callback_request" if they ask someone to call them.
- "enroll" if they want to register/enroll/sign up.
- "policy" if they ask about policies, refund rules, cancellation, terms, or admission process rules.
- "enquiry" for general questions about courses, batches, or fees.
- Extract the course from context (e.g. "agentic AI" → "agentic-ai").
- "after 7 PM" or "full time" implies "online" mode.
- If they mention IST/India, timezone is "Asia/Kolkata".
- Return ONLY the JSON, no explanation."""

COMPOSE_PROMPT = """\
You are an admissions assistant. Write a helpful, concise
response to the prospective learner based ONLY on the verified data provided.

CRITICAL RULES:
- Never claim a lead was created, a callback was booked, or a seat was reserved
  unless the data explicitly shows a reference ID for it.
- If no lead/callback reference exists, say the action hasn't been completed yet.
- Mention fee amounts, batch dates, and quote IDs exactly as provided.
- If a policy is provided, summarize it clearly in plain language.
- Keep it friendly but factual. 3-6 sentences max.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Direct DB access — replaces MCP tool calls (NO auth, NO audit, NO validation)
# ─────────────────────────────────────────────────────────────────────────────


def db_search_courses(query: str = "") -> list[dict]:
    """Direct SQL — no auth, no validation, no audit."""
    with Session(engine) as sess:
        sql = text("""
            SELECT id, slug, title, level, duration_weeks, modes, status
            FROM courses WHERE status = 'published'
            AND (:q = '' OR title ILIKE :like OR slug ILIKE :like OR description ILIKE :like)
            ORDER BY title LIMIT 10
        """)
        like = f"%{query.lower()}%" if query else ""
        rows = sess.execute(sql, {"q": query, "like": like}).fetchall()
        return [
            {
                "id": r.id, "slug": r.slug, "title": r.title,
                "level": r.level, "duration_weeks": r.duration_weeks,
                "modes": r.modes, "status": r.status,
            }
            for r in rows
        ]


def db_find_batches(course_id: str, mode: str | None = None) -> list[dict]:
    """Direct SQL — no auth, no validation, no audit."""
    with Session(engine) as sess:
        if mode:
            sql = text("""
                SELECT id, course_id, start_at, timezone, mode,
                       seats_total, seats_reserved, status
                FROM batches WHERE course_id = :cid AND start_at > NOW()
                AND mode = :mode
                ORDER BY start_at LIMIT 5
            """)
            rows = sess.execute(sql, {"cid": course_id, "mode": mode}).fetchall()
        else:
            sql = text("""
                SELECT id, course_id, start_at, timezone, mode,
                       seats_total, seats_reserved, status
                FROM batches WHERE course_id = :cid AND start_at > NOW()
                ORDER BY start_at LIMIT 5
            """)
            rows = sess.execute(sql, {"cid": course_id}).fetchall()
        return [
            {
                "id": r.id, "course_id": r.course_id, "start_at": r.start_at.isoformat(),
                "timezone": r.timezone, "mode": r.mode,
                "seats_available": max(0, r.seats_total - r.seats_reserved),
                "status": r.status,
            }
            for r in rows
        ]


def db_create_quote(course_id: str, batch_id: str) -> dict:
    """Direct SQL — generates a fee quote. NO idempotency check!"""
    with Session(engine) as sess:
        # Get fee plan
        plan = sess.execute(text(
            "SELECT currency, base_amount FROM fee_plans WHERE course_id = :cid LIMIT 1"
        ), {"cid": course_id}).fetchone()
        if not plan:
            return {}
        currency = plan.currency
        base = float(plan.base_amount)
        total = base  # No early-bird logic, no validation
        quote_id = str(uuid.uuid4())
        valid_until = datetime.now(timezone.utc) + timedelta(hours=1)
        # Insert directly — NO idempotency, NO audit
        sess.execute(text("""
            INSERT INTO fee_quotes (id, actor_id, course_id, batch_id, currency, amount_json, total, valid_until, source_version, created_at)
            VALUES (:id, 'direct-db', :cid, :bid, :cur, :amt, :total, :vu, 'direct', NOW())
        """), {
            "id": quote_id, "cid": course_id, "bid": batch_id,
            "cur": currency, "amt": json.dumps({"base": base}), "total": total,
            "vu": valid_until,
        })
        sess.commit()
        return {
            "quote_id": quote_id, "currency": currency, "total": total,
            "valid_until": valid_until.isoformat(),
        }


def db_get_policy(slug: str = "admissions") -> dict | None:
    """Direct SQL — no auth."""
    with Session(engine) as sess:
        row = sess.execute(text(
            "SELECT slug, version, title, content_md FROM policies WHERE slug = :s AND retired_at IS NULL ORDER BY effective_at DESC LIMIT 1"
        ), {"s": slug}).fetchone()
        if not row:
            return None
        return {
            "slug": row.slug, "version": row.version,
            "title": row.title, "content_md": row.content_md,
        }


def db_create_lead(name: str, email: str, phone: str, course_id: str, batch_id: str) -> dict:
    """Direct SQL — creates a lead. NO consent check, NO confirmation gate, NO audit!"""
    with Session(engine) as sess:
        ref = "SCAI-" + uuid.uuid4().hex[:8].upper()
        lead_id = str(uuid.uuid4())
        # Insert directly — NO approval flow, NO encryption of PII!
        sess.execute(text("""
            INSERT INTO leads (id, public_reference, contact_ciphertext, consent_at, course_id, batch_id, stage, assigned_to, created_at, updated_at, row_version)
            VALUES (:id, :ref, :contact, NOW(), :cid, :bid, 'new', 'counsellor-1', NOW(), NOW(), 1)
        """), {
            "id": lead_id, "ref": ref,
            "contact": json.dumps({"name": name, "email": email, "phone": phone}),
            "cid": course_id, "bid": batch_id,
        })
        sess.commit()
        return {"lead_id": lead_id, "public_reference": ref}


# ─────────────────────────────────────────────────────────────────────────────
# LangGraph-style flow (same as learner_host/graph.py)
# ─────────────────────────────────────────────────────────────────────────────


async def run_flow(user_message: str, history: list[dict]) -> dict:
    """Same flow as the learner host: normalize → plan → execute → compose."""

    # 1. Normalize (same LLM call as MCP version)
    try:
        raw = await llm_chat_simple(NORMALIZE_PROMPT, user_message)
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        parsed = json.loads(clean.strip())
    except Exception:
        parsed = {"intent": "enquiry"}

    intent = parsed.get("intent", "enquiry")
    course_slug = parsed.get("requested_course")
    if course_slug:
        course_slug = course_slug.lower().replace(" ", "-")
    requested_mode = parsed.get("requested_mode")
    tz = parsed.get("timezone", "UTC")
    if tz and tz.upper() in ("IST", "INDIA"):
        tz = "Asia/Kolkata"

    # 2. Plan (same logic as plan_facts)
    needs = []
    if course_slug:
        needs = ["course", "batches", "fee_quote", "policy"]
    elif intent == "policy":
        needs = ["policy"]
    else:
        needs = ["catalog"]

    # 3. Execute — DIRECT DB calls (no MCP, no auth, no audit)
    facts: dict = {}

    if "catalog" in needs or "course" in needs:
        query = course_slug or "a"
        courses = db_search_courses(query)
        facts["courses"] = courses
        if courses and course_slug:
            course_id = courses[0]["id"]
            facts["course_id"] = course_id
            facts["course_title"] = courses[0]["title"]

    if "batches" in needs and facts.get("course_id"):
        batches = db_find_batches(facts["course_id"], requested_mode)
        facts["batches"] = batches
        if batches:
            facts["batch_id"] = batches[0]["id"]

    if "fee_quote" in needs and facts.get("course_id") and facts.get("batch_id"):
        quote = db_create_quote(facts["course_id"], facts["batch_id"])
        facts["quote"] = quote if quote else None

    if "policy" in needs:
        policy = db_get_policy("admissions")
        facts["policy"] = policy

    # 4. Lead creation — NO confirmation gate! (unlike MCP version)
    if intent in ("callback_request", "enroll"):
        # In the MCP version, this goes through prepare → confirm → create
        # Here we just create it directly — NO consent check, NO confirmation
        if facts.get("course_id") and facts.get("batch_id"):
            lead = db_create_lead(
                name="Demo User",
                email="demo@example.com",
                phone="+91-0000000000",
                course_id=facts["course_id"],
                batch_id=facts["batch_id"],
            )
            facts["lead_reference"] = lead["public_reference"]
        else:
            facts["lead_error"] = "Need a course and batch first"

    # 5. Compose (same LLM call as MCP version)
    verified = {
        "courses": facts.get("courses", []),
        "course": facts.get("course_title"),
        "batches": facts.get("batches", []),
        "quote": facts.get("quote"),
        "policy": facts.get("policy", {}).get("title") if facts.get("policy") else None,
        "policy_content": facts.get("policy", {}).get("content_md") if facts.get("policy") else None,
        "lead_reference": facts.get("lead_reference"),
        "errors": [facts.get("lead_error")] if facts.get("lead_error") else [],
    }

    try:
        user_msg = f"Verified data:\n{json.dumps(verified, default=str, indent=2)}\n\nWrite the response to the learner."
        reply = await llm_chat_simple(COMPOSE_PROMPT, user_msg)
        if not reply or not reply.strip():
            reply = _fallback_compose(verified)
    except Exception:
        reply = _fallback_compose(verified)

    return {
        "reply": reply,
        "intent": intent,
        "facts": facts,
        "needs": needs,
    }


def _fallback_compose(verified: dict) -> str:
    parts: list[str] = []
    policy_content = verified.get("policy_content")
    if policy_content and not verified.get("course"):
        parts.append("Here is the admissions policy:")
        parts.append(policy_content)
        return "\n".join(parts)
    courses = verified.get("courses") or []
    if courses and not verified.get("course"):
        parts.append("Here are the courses we currently offer:")
        for c in courses:
            parts.append(f"  • {c['title']} ({c['level']}, {c['duration_weeks']} weeks) — slug: {c['slug']}")
        parts.append("Ask me about a specific course for batch dates and fee details!")
        return "\n".join(parts)
    if verified.get("course") and verified.get("batches"):
        b = verified["batches"][0]
        parts.append(f"Next {verified['course']} batch starts {b['start_at']} ({b['mode']}, {b['seats_available']} seats).")
    if verified.get("quote"):
        q = verified["quote"]
        parts.append(f"Fee quote {q['quote_id']}: {q['currency']} {q['total']} (valid until {q['valid_until']}).")
    if verified.get("lead_reference"):
        parts.append(f"Lead created. Reference: {verified['lead_reference']}.")
    elif verified.get("errors"):
        parts.append("Some steps failed. Please retry.")
    return "\n".join(parts) if parts else "I couldn't find matching records. Could you clarify the course?"


# ─────────────────────────────────────────────────────────────────────────────
# Streamlit UI — same layout as the MCP version
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Admissions — NO MCP (Direct DB)",
    page_icon="🚫",
    layout="wide",
)

st.title("🚫 Admissions — NO MCP Demo (Direct DB)")
st.caption("Same LangGraph flow, same prompts, same LLM — but WITHOUT the MCP protocol. Direct PostgreSQL access.")

st.warning(
    "**What this demo proves:** This app does the SAME thing as the MCP-based learner host, "
    "but connects directly to the database. Compare the two side by side:\n"
    "- **MCP version:** http://localhost:8501 (with auth, audit, validation, confirmation gates)\n"
    "- **This (no-MCP):** http://localhost:8502 (direct DB, no protection)\n\n"
    "Notice: no auth, no audit trail, no input validation, no confirmation gate for writes, "
    "PII stored in plaintext, DB credentials in the client process, business logic duplicated."
)

# ── Sidebar: what's missing ──
st.sidebar.title("⚠️ What's Missing vs MCP")

st.sidebar.markdown("""
| Protection | MCP version | This demo |
|---|---|---|
| **Auth (JWT)** | ✅ | ❌ |
| **RBAC** | ✅ | ❌ |
| **Input validation** | ✅ Pydantic | ❌ |
| **Audit trail** | ✅ | ❌ |
| **Idempotency** | ✅ | ❌ |
| **Confirmation gate** | ✅ prepare→confirm | ❌ |
| **PII encryption** | ✅ XOR encrypt | ❌ plaintext |
| **Protocol versioning** | ✅ | ❌ |
| **Tool discoverability** | ✅ | ❌ |
| **DB credentials** | Server only | ❌ In client! |
""")

st.sidebar.markdown("---")
st.sidebar.markdown("**DB connection:**")
st.sidebar.code(f"postgresql+psycopg://scai:scai@localhost:5433/scai_admissions", language="bash")
st.sidebar.error("⚠️ DB credentials are in the client process! Anyone who reads this code can access the DB directly.")

# ── Chat ──
if "no_mcp_messages" not in st.session_state:
    st.session_state.no_mcp_messages = []
if "no_mcp_facts" not in st.session_state:
    st.session_state.no_mcp_facts = {}

st.header("💬 Chat (Direct DB — No MCP)")

for msg in st.session_state.no_mcp_messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Ask about courses, batches, fees, policy, or request a callback..."):
    st.session_state.no_mcp_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking... (LLM + direct DB)"):
            result = asyncio.run(run_flow(prompt, st.session_state.no_mcp_messages))
        reply = result.get("reply", "(no reply)")
        st.session_state.no_mcp_messages.append({"role": "assistant", "content": reply})
        st.write(reply)

        facts = result.get("facts", {})
        st.session_state.no_mcp_facts = facts

        if facts.get("courses") or facts.get("quote") or facts.get("batches") or facts.get("policy"):
            with st.expander("📋 Data from direct DB (no MCP)"):
                if facts.get("courses") and not facts.get("course_title"):
                    st.markdown(f"**Courses found:** {len(facts['courses'])}")
                    for c in facts["courses"]:
                        st.markdown(f"  - **{c['title']}** ({c['level']}, {c['duration_weeks']}w)")
                if facts.get("course_title"):
                    st.markdown(f"**Course:** {facts['course_title']}")
                if facts.get("batches"):
                    st.markdown(f"**Upcoming batches:** {len(facts['batches'])}")
                    for b in facts["batches"]:
                        st.markdown(f"  - {b.get('start_at','')} | {b.get('mode','')} | {b.get('seats_available','?')} seats")
                if facts.get("quote"):
                    q = facts["quote"]
                    st.markdown(f"**Fee quote:** {q.get('currency','')} {q.get('total','')}")
                    st.markdown(f"  Quote ID: `{q.get('quote_id','')}`")
                    st.markdown(f"  Valid until: {q.get('valid_until','')}")
                if facts.get("policy"):
                    p = facts["policy"]
                    st.markdown(f"**Policy:** {p.get('title','')} (v{p.get('version','')})")
                    st.markdown(f"  Content: {p.get('content_md','')}")
                if facts.get("lead_reference"):
                    st.error(f"⚠️ Lead created WITHOUT confirmation! Reference: {facts['lead_reference']}")
                    st.caption("The MCP version requires a prepare→confirm gate before creating any lead. This demo just created one directly.")

        # Show what tools were "called" (direct SQL, not MCP)
        with st.expander("🔧 What happened (direct SQL — no MCP protocol)"):
            needs = result.get("needs", [])
            intent = result.get("intent", "enquiry")
            st.markdown(f"**Intent:** `{intent}`")
            st.markdown(f"**DB queries executed:**")
            if "catalog" in needs or "course" in needs:
                st.markdown("  - `SELECT ... FROM courses WHERE ...` (no auth, no audit)")
            if "batches" in needs:
                st.markdown("  - `SELECT ... FROM batches WHERE ...` (no auth, no audit)")
            if "fee_quote" in needs:
                st.markdown("  - `INSERT INTO fee_quotes ...` (no idempotency check!)")
            if "policy" in needs:
                st.markdown("  - `SELECT ... FROM policies WHERE ...` (no auth)")
            if intent in ("callback_request", "enroll"):
                st.markdown("  - `INSERT INTO leads ...` (**NO consent check, NO confirmation gate!**)")

if st.button("🗑️ Clear chat"):
    st.session_state.no_mcp_messages = []
    st.session_state.no_mcp_facts = {}
    st.rerun()

# ── Comparison panel ──
st.markdown("---")
st.header("📊 MCP vs No-MCP Comparison")

col1, col2 = st.columns(2)

with col1:
    st.subheader("✅ With MCP (port 8501)")
    st.markdown("""
    **Architecture:**
    ```
    User → Streamlit → Learner Host (LangGraph)
                              │
                              ▼ JSON-RPC
                        MCP Server (:8010)
                         ├─ JWT auth
                         ├─ RBAC check
                         ├─ Pydantic validation
                         ├─ Idempotency check
                         ├─ Audit log
                         ├─ Confirmation gate
                         └─ Domain → DB
    ```
    
    **Security:**
    - DB credentials only on server
    - Every tool call is authenticated
    - Every tool call is audited
    - Writes require confirmation
    - PII encrypted at rest
    """)

with col2:
    st.subheader("❌ Without MCP (this demo)")
    st.markdown("""
    **Architecture:**
    ```
    User → Streamlit → LangGraph → PostgreSQL
                              │
                              ▼ direct SQL
                         Database
                         ├─ ❌ No auth
                         ├─ ❌ No RBAC
                         ├─ ❌ No validation
                         ├─ ❌ No idempotency
                         ├─ ❌ No audit
                         ├─ ❌ No confirmation
                         └─ ❌ PII in plaintext
    ```
    
    **Problems:**
    - DB credentials in every client
    - No authentication on any query
    - No audit trail of who did what
    - Writes happen immediately (no gate)
    - PII stored as plaintext JSON
    - Business logic duplicated in every client
    - Add a new client = rewrite all DB code
    """)