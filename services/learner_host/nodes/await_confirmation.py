"""Node: await_confirmation — use a LangGraph interrupt and persist graph state.

The host must never claim "callback booked" from model text alone. It pauses
here until the user confirms the exact preview.
"""

from __future__ import annotations

from langgraph.types import interrupt

from services.learner_host.state import LearnerState


def await_confirmation(state: LearnerState) -> LearnerState:
    preview = state.get("pending_action_preview")
    if preview is None:
        return {**state, "confirmed": False,
                "errors": state.get("errors", []) + [{"confirm": "no pending preview"}]}
    # interrupt pauses the graph; the API layer resumes with the user's answer.
    answer = interrupt({"prompt": "Confirm the action below?", "preview": preview})
    return {**state, "confirmed": bool(answer)}


__all__ = ["await_confirmation"]