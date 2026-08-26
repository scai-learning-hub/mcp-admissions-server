"""Counsellor host state — separate from the learner host's state.

The counsellor has a DIFFERENT intent set: list leads, prepare for callbacks,
update stages. It never creates leads (that's the learner's job).
"""

from __future__ import annotations

from typing import Any, TypedDict


class CounsellorState(TypedDict, total=False):
    thread_id: str
    actor_id: str
    messages: list[Any]
    intent: str | None
    target_lead_id: str | None
    target_lead_ref: str | None
    requested_course: str | None
    requested_mode: str | None
    discovered_tools: list[dict[str, Any]]
    facts: dict[str, Any]
    leads: list[dict[str, Any]]
    current_lead: dict[str, Any] | None
    new_stage: str | None
    stage_note: str | None
    confirmed: bool | None
    pending_action: str | None
    tool_results: dict[str, Any]
    errors: list[dict[str, Any]]


__all__ = ["CounsellorState"]