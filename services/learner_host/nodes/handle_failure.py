"""Node: handle_failure — stable error reference and safe next action."""

from __future__ import annotations

from services.learner_host.state import LearnerState


def handle_failure(state: LearnerState) -> LearnerState:
    errors = state.get("errors", [])
    if not errors:
        return state
    text = "Something went wrong. Please retry or contact admissions@schoolofcore.ai."
    messages = state.get("messages", []) + [{"role": "assistant", "content": text}]
    return {**state, "messages": messages}


__all__ = ["handle_failure"]