"""Node: await_confirmation — pause for counsellor confirmation before a stage update.

Mirrors the learner host's confirmation pattern but with a different prompt.
The server still enforces authorization independently.
"""

from __future__ import annotations

from langgraph.types import interrupt

from services.counsellor_host.state import CounsellorState


def await_confirmation(state: CounsellorState) -> CounsellorState:
    if state.get("pending_action") != "update_stage":
        return {**state, "confirmed": True}  # no confirmation needed for reads

    lead = state.get("facts", {}).get("current_lead", {})
    preview = {
        "action": "update_stage",
        "lead_id": state.get("target_lead_id"),
        "lead_ref": lead.get("public_reference", state.get("target_lead_ref")),
        "new_stage": state.get("new_stage"),
    }
    answer = interrupt({"prompt": "Confirm stage update?", "preview": preview})
    return {**state, "confirmed": bool(answer)}


__all__ = ["await_confirmation"]