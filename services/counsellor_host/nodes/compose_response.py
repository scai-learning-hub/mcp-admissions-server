"""Node: compose — build the counsellor's response from typed tool results."""

from __future__ import annotations

from services.counsellor_host.prompts import pre_call_brief, stage_update_guide
from services.counsellor_host.state import CounsellorState


def compose_response(state: CounsellorState) -> CounsellorState:
    intent = state.get("intent", "list_leads")
    facts = state.get("facts", {})
    parts: list[str] = []

    if intent == "list_leads":
        leads = facts.get("leads", [])
        if not leads:
            parts.append("You have no assigned leads today.")
        else:
            parts.append(f"You have {len(leads)} assigned lead(s):")
            for l in leads:
                parts.append(
                    f"  • {l.get('public_reference','')} | stage={l.get('stage','')} | "
                    f"course={l.get('course_id','')[:8]}... | created={l.get('created_at','')}"
                )

    elif intent == "lead_summary":
        lead = facts.get("current_lead")
        if lead:
            parts.append(f"Lead {lead.get('public_reference','')} — stage: {lead.get('stage','')}")
            parts.append(f"  Course: {lead.get('course_id','')}")
            parts.append(f"  Created: {lead.get('created_at','')}")
            cbs = lead.get("callbacks", [])
            parts.append(f"  Callbacks: {len(cbs)}")
            for cb in cbs:
                parts.append(f"    - {cb.get('callback_id','')[:8]}... status={cb.get('status','')}")
        else:
            parts.append("Lead not found or not assigned to you.")

    elif intent == "prepare_callback":
        lead = facts.get("current_lead")
        if lead:
            brief = pre_call_brief(
                lead_ref=lead.get("public_reference", ""),
                course_id=lead.get("course_id", ""),
                stage=lead.get("stage", ""),
                callback_count=len(lead.get("callbacks", [])),
            )
            parts.append(brief)
        else:
            parts.append("Lead not found.")

    elif intent == "update_stage":
        lead = facts.get("current_lead", {})
        if state.get("confirmed") and state.get("tool_results", {}).get("stage_update"):
            result = state["tool_results"]["stage_update"]
            parts.append(f"Stage updated: {lead.get('public_reference','')} → "
                         f"{result.get('stage','')} (version {result.get('row_version','')})")
        elif state.get("pending_action") == "update_stage" and not state.get("confirmed"):
            parts.append("Stage update was prepared but not confirmed.")
        elif lead:
            guide = stage_update_guide(
                lead_ref=lead.get("public_reference", ""),
                current_stage=lead.get("stage", ""),
                new_stage=state.get("new_stage", ""),
                note="counsellor chat",
            )
            parts.append(guide)
        else:
            parts.append("Could not find the lead to update.")

    # --- Common tools (shared with learner host) ---

    elif intent == "search_courses":
        courses = facts.get("courses", [])
        if courses:
            parts.append(f"Found {len(courses)} course(s):")
            for c in courses:
                parts.append(
                    f"  • {c.get('title','')} ({c.get('level','')}, {c.get('duration_weeks','')}w) — slug: {c.get('slug','')}"
                )
        else:
            parts.append("No courses found.")

    elif intent == "course_details":
        course = facts.get("course_detail")
        if course:
            parts.append(f"Course: {course.get('title','')}")
            parts.append(f"  Level: {course.get('level','')} | Duration: {course.get('duration_weeks','')} weeks")
            parts.append(f"  Modes: {', '.join(course.get('modes', []))}")
            parts.append(f"  Status: {course.get('status','')}")
            topics = course.get("topics", [])
            if topics:
                parts.append(f"  Topics: {', '.join(topics)}")
            desc = course.get("description", "")
            if desc:
                parts.append(f"  Description: {desc}")
        else:
            parts.append("Course not found.")

    elif intent == "batches":
        batches = facts.get("batches", [])
        course_title = facts.get("course_title", "")
        if batches:
            parts.append(f"Upcoming batches for {course_title}:")
            for b in batches:
                seats = b.get("seats", {})
                parts.append(
                    f"  • {b.get('start_at','')} | {b.get('mode','')} | "
                    f"{seats.get('seats_available','?')} seats available | {b.get('status','')}"
                )
        else:
            parts.append(f"No upcoming batches found for {course_title or 'the requested course'}.")

    elif intent == "fee_quote":
        quote = facts.get("quote")
        course_title = facts.get("course_title", "")
        if quote:
            parts.append(f"Fee quote for {course_title}:")
            parts.append(f"  Quote ID: {quote.get('quote_id','')}")
            parts.append(f"  Total: {quote.get('currency','')} {quote.get('total','')}")
            parts.append(f"  Valid until: {quote.get('valid_until','')}")
            breakdown = quote.get("breakdown", [])
            if breakdown:
                parts.append("  Breakdown:")
                for item in breakdown:
                    parts.append(f"    - {item.get('label','')}: {quote.get('currency','')} {item.get('amount','')}")
        else:
            parts.append(f"Could not generate a fee quote for {course_title or 'the requested course'}.")

    elif intent == "policy":
        policy = facts.get("policy")
        if policy:
            parts.append(f"Policy: {policy.get('title','')}")
            parts.append(f"  Version: {policy.get('version','')}")
            content = policy.get("content_md", "")
            if content:
                # Show first 500 chars to keep response manageable
                preview = content[:500] + ("..." if len(content) > 500 else "")
                parts.append(f"  Content: {preview}")
        else:
            parts.append("No policy found.")

    if state.get("errors"):
        parts.append("Errors: " + "; ".join(str(e) for e in state["errors"]))

    text = "\n".join(parts) if parts else "I couldn't process that request."
    messages = state.get("messages", []) + [{"role": "assistant", "content": text}]
    return {**state, "messages": messages}


__all__ = ["compose_response"]