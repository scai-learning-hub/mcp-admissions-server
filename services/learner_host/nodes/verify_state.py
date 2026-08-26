"""Node: verify_state — read the returned lead/callback reference."""

from __future__ import annotations

from services.learner_host.state import LearnerState


async def verify_state(state: LearnerState) -> LearnerState:
    # Verification: only trust typed tool results, never model text.
    client: LearnerMCPClient = state["_client"]  # type: ignore[literal-required]
    facts = state.get("facts", {})
    if not state.get("lead_reference"):
        return state
    # We could call leads.get_summary if the learner had permission; learners do
    # not, so verification here is simply that a non-empty reference was returned
    # by the typed result. This is the safety guarantee.
    return {**state, "tool_results": {
        "lead_reference": state.get("lead_reference"),
        "callback_reference": state.get("callback_reference"),
        "quote_id": state.get("quote_id"),
    }}


__all__ = ["verify_state"]