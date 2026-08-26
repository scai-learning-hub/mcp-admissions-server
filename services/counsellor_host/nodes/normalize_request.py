"""Node: normalize — use LLM to extract the counsellor's intent from free text.

Separate from the learner host's normalize. Different intent set.
"""

from __future__ import annotations

import json
import re

from packages.shared.llm import get_llm
from services.counsellor_host.state import CounsellorState

SYSTEM_PROMPT = """\
You are the intent extraction layer for a counsellor console.
Extract structured information from the counsellor's message. Do NOT invent facts.

Return ONLY a JSON object with these fields (omit fields you can't determine):
{
  "intent": "list_leads" | "lead_summary" | "prepare_callback" | "update_stage"
           | "search_courses" | "course_details" | "batches" | "fee_quote" | "policy",
  "target_lead_ref": "SCAI-XXXX" or null,
  "new_stage": "contacted" | "qualified" | "enrolled" | "dropped" | "new" | null,
  "requested_course": "agentic-ai" | "aiops" | "mlops" | "gen-ai" | null,
  "requested_mode": "online" | "in_person" | "hybrid" | null
}

Rules:
- "list_leads" for showing/listing leads.
- "lead_summary" for details about a specific lead.
- "prepare_callback" for callback/call preparation.
- "update_stage" for advancing/updating lead stage.
- "search_courses" for browsing/searching the course catalog.
- "course_details" for getting details of a specific course.
- "batches" for checking upcoming batch schedules.
- "fee_quote" for generating a fee quote for a course+batch.
- "policy" for reading admissions policies.
- Extract SCAI-XXXX references if mentioned.
- Extract the course from context (e.g. "agentic AI" -> "agentic-ai").
- Return ONLY the JSON, no explanation."""

LEAD_REF_RE = re.compile(r"\b(SCAI-[A-Z0-9]+)\b", re.IGNORECASE)


async def normalize_request(state: CounsellorState) -> CounsellorState:
    messages = state.get("messages", [])
    last = ""
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            last = m.get("content", "")
            break

    try:
        llm = get_llm()
        response = await llm.chat_simple(SYSTEM_PROMPT, last or "")
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        parsed = json.loads(text)

        return {
            **state,
            "intent": parsed.get("intent", "list_leads"),
            "target_lead_ref": parsed.get("target_lead_ref"),
            "new_stage": parsed.get("new_stage"),
            "requested_course": parsed.get("requested_course"),
            "requested_mode": parsed.get("requested_mode"),
            "errors": [],
        }
    except Exception:
        return _fallback(state, last)


def _fallback(state: CounsellorState, text: str) -> CounsellorState:
    text_lower = (text or "").lower()
    intent = "list_leads"
    if any(w in text_lower for w in ["callback", "call", "brief", "prepare"]):
        intent = "prepare_callback"
    if any(w in text_lower for w in ["update", "move", "stage", "advance"]):
        intent = "update_stage"
    if any(w in text_lower for w in ["summary", "detail", "show lead", "lead info"]):
        intent = "lead_summary"
    if any(w in text_lower for w in ["search course", "find course", "what course", "catalog", "list course"]):
        intent = "search_courses"
    if any(w in text_lower for w in ["course detail", "course info", "tell me about course"]):
        intent = "course_details"
    if any(w in text_lower for w in ["batch", "schedule", "upcoming", "next class", "start date"]):
        intent = "batches"
    if any(w in text_lower for w in ["fee", "quote", "price", "cost", "tuition"]):
        intent = "fee_quote"
    if any(w in text_lower for w in ["policy", "refund", "cancellation", "admission policy"]):
        intent = "policy"

    ref_match = LEAD_REF_RE.search(text or "")
    target_lead_ref = ref_match.group(1).upper() if ref_match else None

    stage_match = re.search(r"\b(contacted|qualified|enrolled|dropped|new)\b", text_lower)
    new_stage = stage_match.group(1) if stage_match else None

    # Course extraction
    requested_course = None
    if "agentic" in text_lower:
        requested_course = "agentic-ai"
    elif "gen ai" in text_lower or "generative" in text_lower:
        requested_course = "gen-ai"
    elif "aiops" in text_lower:
        requested_course = "aiops"
    elif "mlops" in text_lower:
        requested_course = "mlops"

    requested_mode = None
    if "online" in text_lower:
        requested_mode = "online"
    elif "in person" in text_lower or "in-person" in text_lower or "classroom" in text_lower:
        requested_mode = "in_person"
    elif "hybrid" in text_lower:
        requested_mode = "hybrid"

    return {
        **state, "intent": intent, "target_lead_ref": target_lead_ref,
        "new_stage": new_stage, "requested_course": requested_course,
        "requested_mode": requested_mode, "errors": [],
    }


__all__ = ["normalize_request"]