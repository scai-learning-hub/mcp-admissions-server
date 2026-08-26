"""Node: compose_response — use LLM to generate a natural response from typed results.

The host must never claim "callback booked" from model text alone. It may say
that only after receiving a successful typed result containing the callback
reference. So we feed the LLM the VERIFIED tool results and tell it to base
its response only on them.
"""

from __future__ import annotations

import json

from packages.shared.llm import get_llm
from services.learner_host.state import LearnerState

SYSTEM_PROMPT = """\
You are an admissions assistant at School of Core AI. Write a helpful, concise
response to the prospective learner based ONLY on the verified data provided.

CRITICAL RULES:
- Never claim a lead was created, a callback was booked, or a seat was reserved
  unless the data explicitly shows a reference ID for it.
- If no lead/callback reference exists, say the action hasn't been completed yet.
- Mention fee amounts, batch dates, and quote IDs exactly as provided.
- If a policy is provided, summarize it clearly in plain language.
- Keep it friendly but factual. 3-6 sentences max.
"""


async def compose_response(state: LearnerState) -> LearnerState:
    facts = state.get("facts", {})
    tool_results = state.get("tool_results", {})

    # Build a structured summary of verified facts for the LLM
    verified = {
        "courses": facts.get("courses", []),
        "course": facts.get("course_title"),
        "batches": facts.get("batches", []),
        "quote": facts.get("quote"),
        "policy": facts.get("policy", {}).get("title") if facts.get("policy") else None,
        "policy_content": facts.get("policy", {}).get("content_md") if facts.get("policy") else None,
        "lead_reference": state.get("lead_reference"),
        "callback_reference": state.get("callback_reference"),
        "pending_preview": state.get("pending_action_preview") is not None,
        "confirmed": state.get("confirmed"),
        "errors": state.get("errors", []),
    }

    try:
        llm = get_llm()
        user_msg = f"Verified tool results:\n{json.dumps(verified, default=str, indent=2)}\n\nWrite the response to the learner."
        reply = await llm.chat_simple(SYSTEM_PROMPT, user_msg)
        if not reply or not reply.strip():
            reply = _fallback_compose(verified)
    except Exception:
        reply = _fallback_compose(verified)

    messages = state.get("messages", []) + [{"role": "assistant", "content": reply}]
    return {**state, "messages": messages}


def _fallback_compose(verified: dict) -> str:
    parts: list[str] = []
    # Policy-specific response
    policy_content = verified.get("policy_content")
    if policy_content and not verified.get("course"):
        parts.append("Here is the admissions policy:")
        parts.append(policy_content)
        return "\n".join(parts)
    # General catalogue listing (no specific course selected)
    courses = verified.get("courses") or []
    if courses and not verified.get("course"):
        parts.append("Here are the courses we currently offer:")
        for c in courses:
            parts.append(f"  • {c['title']} ({c['level']}, {c['duration_weeks']} weeks) — slug: {c['slug']}")
        parts.append("Ask me about a specific course for batch dates and fee details!")
        return "\n".join(parts)
    if verified.get("course") and verified.get("batches"):
        b = verified["batches"][0]
        parts.append(f"Next {verified['course']} batch starts {b['start_at']} ({b['mode']}, {b['seats']['seats_available']} seats).")
    if verified.get("quote"):
        q = verified["quote"]
        parts.append(f"Fee quote {q['quote_id']}: {q['currency']} {q['total']} (valid until {q['valid_until']}).")
    if verified.get("lead_reference"):
        parts.append(f"Lead created. Reference: {verified['lead_reference']}.")
        if verified.get("callback_reference"):
            parts.append(f"Callback scheduled. Reference: {verified['callback_reference']}.")
    elif verified.get("pending_preview") and not verified.get("confirmed"):
        parts.append("A lead preview was prepared. Confirm to create the lead.")
    elif verified.get("errors"):
        parts.append("Some steps failed. Please retry.")
    return "\n".join(parts) if parts else "I couldn't find matching records. Could you clarify the course?"


__all__ = ["compose_response"]