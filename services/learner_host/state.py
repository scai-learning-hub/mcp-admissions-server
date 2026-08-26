"""LangGraph state definition (plan §9).

The host must never claim "callback booked" from model text alone. It may say
that only after receiving a successful typed result containing the callback
reference.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import MessagesState  # noqa: F401  (re-exported for convenience)


class LearnerState(TypedDict, total=False):
    thread_id: str
    actor_id: str
    messages: list[Any]
    intent: str | None
    requested_course: str | None
    requested_mode: str | None
    timezone: str | None
    discovered_tools: list[dict[str, Any]]
    facts: dict[str, Any]
    quote_id: str | None
    pending_approval_id: str | None
    pending_action_preview: dict[str, Any] | None
    confirmed: bool | None
    tool_results: dict[str, Any]
    lead_reference: str | None
    callback_reference: str | None
    errors: list[dict[str, Any]]


__all__ = ["LearnerState"]