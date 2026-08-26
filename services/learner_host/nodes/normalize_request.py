"""Node: normalize_request — extract explicit constraints using LLM.

The LLM understands free-text like "I work full-time, can someone call me
after 7 PM?" and extracts structured intent. It does NOT invent facts —
it only extracts what the user said. The MCP tools remain the source of truth.
"""

from __future__ import annotations

import json

from packages.shared.llm import get_llm
from services.learner_host.state import LearnerState

SYSTEM_PROMPT = """\
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


async def normalize_request(state: LearnerState) -> LearnerState:
    """Use LLM to extract structured intent from the user's message."""
    messages = state.get("messages", [])
    last = ""
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            last = m.get("content", "")
            break
        if hasattr(m, "type") and m.type == "human":
            last = m.content if isinstance(m.content, str) else str(m.content)
            break

    try:
        llm = get_llm()
        response = await llm.chat_simple(SYSTEM_PROMPT, last or "")
        # Parse the JSON response
        text = response.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        parsed = json.loads(text)

        # Normalize course slug (model may return "agentic AI" not "agentic-ai")
        course = parsed.get("requested_course")
        if course:
            course = course.lower().replace(" ", "-")
        # Normalize timezone (model may return "IST" not "Asia/Kolkata")
        tz = parsed.get("timezone", "UTC")
        if tz and tz.upper() in ("IST", "INDIA", "INDIAN STANDARD TIME"):
            tz = "Asia/Kolkata"

        return {
            **state,
            "intent": parsed.get("intent", "enquiry"),
            "requested_course": course,
            "requested_mode": parsed.get("requested_mode"),
            "timezone": tz or "UTC",
            "errors": [],
        }
    except Exception as e:
        # Fallback to keyword matching if LLM fails
        return _fallback_normalize(state, last)


def _fallback_normalize(state: LearnerState, text: str) -> LearnerState:
    """Keyword-based fallback if the LLM is unavailable."""
    text_lower = (text or "").lower()
    course_keywords = {
        "agentic ai": "agentic-ai", "aiops": "aiops", "mlops": "mlops",
        "gen ai": "gen-ai", "generative ai": "gen-ai",
        "data science": "data-science", "python": "python",
    }
    requested_course = None
    for kw, slug in course_keywords.items():
        if kw in text_lower:
            requested_course = slug
            break

    requested_mode = None
    for kw in ["online", "after 7", "after work", "weekend"]:
        if kw in text_lower:
            requested_mode = "online"
            break

    intent = "enquiry"
    if any(w in text_lower for w in ["callback", "call me", "phone me"]):
        intent = "callback_request"
    if any(w in text_lower for w in ["enroll", "register", "sign up"]):
        intent = "enroll"
    if any(w in text_lower for w in ["policy", "refund", "cancellation", "terms", "admission process rules"]):
        intent = "policy"

    return {
        **state,
        "intent": intent,
        "requested_course": requested_course,
        "requested_mode": requested_mode,
        "timezone": "Asia/Kolkata" if "ist" in text_lower or "india" in text_lower else "UTC",
        "errors": [],
    }


__all__ = ["normalize_request"]