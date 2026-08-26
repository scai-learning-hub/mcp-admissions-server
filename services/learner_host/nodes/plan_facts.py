"""Node: plan_facts — decide which information must be retrieved."""

from __future__ import annotations

from services.learner_host.state import LearnerState


def plan_facts(state: LearnerState) -> LearnerState:
    intent = state.get("intent", "enquiry")
    course = state.get("requested_course")
    needs: list[str] = []

    if course:
        needs.append("course")
        needs.append("batches")
        needs.append("fee_quote")
        needs.append("policy")
    elif intent == "policy":
        # Policy-specific enquiry — fetch the admissions policy
        needs.append("policy")
    else:
        # General enquiry with no specific course — still show the catalog
        needs.append("catalog")
    if intent in {"callback_request", "enroll"}:
        needs.append("lead_prepare")

    return {**state, "facts": {"needs": needs}}


__all__ = ["plan_facts"]