"""MCP prompts — versioned templates, not hidden business rules (plan §7.3).

Fee calculations, capacity, and eligibility remain deterministic domain logic.
Prompts are shared intake structures so each host doesn't hard-code them.
"""

from __future__ import annotations

PROMPT_VERSION = "1"

ADMISSIONS_QUALIFY_ENQUIRY = """\
You are an admissions assistant at School of Core AI. Qualify the enquiry
using ONLY the facts the learner has provided. Do not invent schedule, fee,
or batch details — those come from MCP tools.

Course interest: {course_interest}
Experience: {experience}
Schedule constraints: {schedule}

Ask for any missing minimum detail (name, phone, email, preferred mode) before
preparing a lead. Never claim a callback is booked unless a tool returned a
callback reference.
"""

COUNSELLOR_PREPARE_CALLBACK = """\
Prepare a pre-call brief for the lead below. Use only data returned by MCP
tools (leads.get_summary, policies.get_current). Do not disclose other leads.

Lead reference: {lead_reference}

Outline:
1. Confirm the learner's course and batch interest.
2. State the applicable admissions policy highlights.
3. Confirm the requested callback window.
4. Set a next stage (new → contacted → qualified).
"""


def admissions_qualify_enquiry(
    course_interest: str, experience: str, schedule: str
) -> dict:
    return {
        "version": PROMPT_VERSION,
        "template": ADMISSIONS_QUALIFY_ENQUIRY.format(
            course_interest=course_interest,
            experience=experience,
            schedule=schedule,
        ),
    }


def counsellor_prepare_callback(lead_reference: str) -> dict:
    return {
        "version": PROMPT_VERSION,
        "template": COUNSELLOR_PREPARE_CALLBACK.format(lead_reference=lead_reference),
    }


__all__ = [
    "PROMPT_VERSION",
    "admissions_qualify_enquiry",
    "counsellor_prepare_callback",
]