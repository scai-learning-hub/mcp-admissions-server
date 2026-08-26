"""Counsellor host prompts — separate from learner host prompts.

These produce pre-call briefs and stage-update guidance. They do NOT contain
fee logic or eligibility rules — those remain deterministic domain logic in
the MCP server.
"""

from __future__ import annotations

COUNSELLOR_PROMPT_VERSION = "1"

PRE_CALL_BRIEF = """\
You are a counsellor preparing to call a lead. Use ONLY
the lead summary returned by MCP tools. Do not disclose other leads.

Lead: {lead_ref}
Course: {course_id}
Stage: {stage}
Callbacks: {callback_count}

Prepare:
1. Greeting and purpose of the call.
2. Confirm the learner's course interest.
3. Highlight the applicable admissions policy.
4. Propose a next stage (contacted → qualified → enrolled).
"""

STAGE_UPDATE_GUIDE = """\
Suggested stage transition for lead {lead_ref}:
  current: {current_stage}
  proposed: {new_stage}
  reason: {note}
Confirm before updating.
"""


def pre_call_brief(lead_ref: str, course_id: str, stage: str, callback_count: int) -> str:
    return PRE_CALL_BRIEF.format(
        lead_ref=lead_ref, course_id=course_id, stage=stage, callback_count=callback_count,
    )


def stage_update_guide(lead_ref: str, current_stage: str, new_stage: str, note: str) -> str:
    return STAGE_UPDATE_GUIDE.format(
        lead_ref=lead_ref, current_stage=current_stage, new_stage=new_stage, note=note,
    )


__all__ = ["COUNSELLOR_PROMPT_VERSION", "pre_call_brief", "stage_update_guide"]