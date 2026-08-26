"""Node: prepare_write — call leads.prepare and produce the exact preview.

This does NOT write a lead. It creates a pending approval only.
"""

from __future__ import annotations

from datetime import datetime, timezone

from services.learner_host.client_registry import get_client
from services.learner_host.state import LearnerState


async def prepare_write(state: LearnerState) -> LearnerState:
    client = get_client(state.get("thread_id", ""))
    if client is None:
        return {**state, "errors": state.get("errors", []) + [{"prepare": "no client"}]}
    facts = state.get("facts", {})
    course_id = facts.get("course_id")
    batch_id = facts.get("batch_id")
    if not course_id or not batch_id:
        return {**state, "errors": state.get("errors", []) + [{"prepare": "missing course/batch"}]}

    # In a real host, these come from the conversation. Demo values:
    contact = {
        "name": "Demo Learner",
        "phone": "+919999900000",
        "email": "demo.learner@example.com",
        "timezone": state.get("timezone", "UTC"),
    }
    args = {
        "contact": contact,
        "course_id": course_id,
        "batch_id": batch_id,
        "consent": True,
        "consent_at": datetime.now(timezone.utc).isoformat(),
        "requested_callback": None,
    }
    res = await client.call_tool("leads_prepare", args)
    if res.get("ok"):
        data = res["data"]
        state["pending_approval_id"] = data.get("approval_id")
        state["pending_action_preview"] = data.get("preview")
    else:
        state["errors"] = state.get("errors", []) + [{"prepare": res.get("error", {})}]
    return state


__all__ = ["prepare_write"]