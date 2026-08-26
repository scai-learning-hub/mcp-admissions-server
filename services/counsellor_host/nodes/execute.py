"""Node: execute — call the right MCP tool based on counsellor intent.

The counsellor can: list assigned leads, get a lead summary, update a stage.
The counsellor CANNOT create leads — the server enforces this via RBAC.
"""

from __future__ import annotations

from services.counsellor_host.client_registry import get_client
from services.counsellor_host.state import CounsellorState


async def execute(state: CounsellorState) -> CounsellorState:
    client = get_client(state.get("thread_id", ""))
    if client is None:
        return {**state, "errors": state.get("errors", []) + [{"execute": "no client"}]}
    intent = state.get("intent", "list_leads")
    facts: dict = {}

    if intent == "list_leads":
        res = await client.call_tool("leads_list_assigned", {"limit": 20})
        if res.get("ok"):
            facts["leads"] = res["data"].get("leads", [])
        else:
            state["errors"] = state.get("errors", []) + [res.get("error", {})]

    elif intent == "lead_summary":
        # Need a lead_id. If we only have a public_reference, list leads to find it.
        lead_id = state.get("target_lead_id")
        if not lead_id:
            # Try to find by public_reference
            res = await client.call_tool("leads_list_assigned", {"limit": 50})
            if res.get("ok"):
                for lead in res["data"].get("leads", []):
                    if lead.get("public_reference", "").upper() == (state.get("target_lead_ref") or "").upper():
                        lead_id = lead.get("lead_id")
                        break
        if lead_id:
            res = await client.call_tool("leads_get_summary", {"lead_id": lead_id})
            if res.get("ok"):
                facts["current_lead"] = res["data"].get("lead")
                state["target_lead_id"] = lead_id
            else:
                state["errors"] = state.get("errors", []) + [res.get("error", {})]
        else:
            state["errors"] = state.get("errors", []) + [{"lead": "not found"}]

    elif intent == "update_stage":
        # Gather lead first if needed
        lead_id = state.get("target_lead_id")
        if not lead_id and state.get("target_lead_ref"):
            res = await client.call_tool("leads_list_assigned", {"limit": 50})
            if res.get("ok"):
                for lead in res["data"].get("leads", []):
                    if lead.get("public_reference", "").upper() == (state.get("target_lead_ref") or "").upper():
                        lead_id = lead.get("lead_id")
                        facts["current_lead"] = lead
                        break
        if lead_id and state.get("new_stage"):
            state["target_lead_id"] = lead_id
            state["pending_action"] = "update_stage"
            # Don't execute yet — need confirmation (like the learner host)
        elif not lead_id:
            state["errors"] = state.get("errors", []) + [{"lead": "not found"}]

    elif intent == "prepare_callback":
        lead_id = state.get("target_lead_id")
        if not lead_id and state.get("target_lead_ref"):
            res = await client.call_tool("leads_list_assigned", {"limit": 50})
            if res.get("ok"):
                for lead in res["data"].get("leads", []):
                    if lead.get("public_reference", "").upper() == (state.get("target_lead_ref") or "").upper():
                        lead_id = lead.get("lead_id")
                        facts["current_lead"] = lead
                        break
        if lead_id:
            state["target_lead_id"] = lead_id
            # Get the summary for the pre-call brief
            res = await client.call_tool("leads_get_summary", {"lead_id": lead_id})
            if res.get("ok"):
                facts["current_lead"] = res["data"].get("lead")

    # --- Common tools (shared with learner host) ---

    elif intent == "search_courses":
        query = state.get("requested_course") or ""
        res = await client.call_tool("catalog_search_courses", {"query": query or "a"})
        if res.get("ok"):
            facts["courses"] = res["data"].get("courses", [])
        else:
            state["errors"] = state.get("errors", []) + [res.get("error", {})]

    elif intent == "course_details":
        slug = state.get("requested_course") or ""
        if slug:
            res = await client.call_tool("catalog_get_course", {"slug_or_id": slug})
            if res.get("ok"):
                facts["course_detail"] = res["data"].get("course")
            else:
                state["errors"] = state.get("errors", []) + [res.get("error", {})]
        else:
            state["errors"] = state.get("errors", []) + [{"course": "no course specified"}]

    elif intent == "batches":
        course_slug = state.get("requested_course") or ""
        if course_slug:
            # Find course_id first
            search_res = await client.call_tool("catalog_search_courses", {"query": course_slug})
            if search_res.get("ok"):
                courses = search_res["data"].get("courses", [])
                if courses:
                    course_id = courses[0]["id"]
                    facts["course_title"] = courses[0]["title"]
                    mode = state.get("requested_mode")
                    batch_res = await client.call_tool("batches_find_upcoming", {
                        "course_id": course_id,
                        "mode": mode,
                        "timezone": "Asia/Kolkata",
                    })
                    if batch_res.get("ok"):
                        facts["batches"] = batch_res["data"].get("batches", [])
                        if facts["batches"]:
                            facts["course_id"] = course_id
                    else:
                        state["errors"] = state.get("errors", []) + [batch_res.get("error", {})]
                else:
                    state["errors"] = state.get("errors", []) + [{"course": "not found"}]
            else:
                state["errors"] = state.get("errors", []) + [search_res.get("error", {})]
        else:
            state["errors"] = state.get("errors", []) + [{"course": "no course specified"}]

    elif intent == "fee_quote":
        course_slug = state.get("requested_course") or ""
        if course_slug:
            search_res = await client.call_tool("catalog_search_courses", {"query": course_slug})
            if search_res.get("ok"):
                courses = search_res["data"].get("courses", [])
                if courses:
                    course_id = courses[0]["id"]
                    facts["course_title"] = courses[0]["title"]
                    batch_res = await client.call_tool("batches_find_upcoming", {
                        "course_id": course_id,
                        "timezone": "Asia/Kolkata",
                    })
                    if batch_res.get("ok"):
                        batches = batch_res["data"].get("batches", [])
                        if batches:
                            batch_id = batches[0]["id"]
                            facts["batch_id"] = batch_id
                            facts["batch_start"] = batches[0]["start_at"]
                            quote_res = await client.call_tool("fees_create_quote", {
                                "course_id": course_id,
                                "batch_id": batch_id,
                            })
                            if quote_res.get("ok"):
                                facts["quote"] = quote_res["data"].get("quote")
                            else:
                                state["errors"] = state.get("errors", []) + [quote_res.get("error", {})]
                        else:
                            state["errors"] = state.get("errors", []) + [{"batches": "none available"}]
                    else:
                        state["errors"] = state.get("errors", []) + [batch_res.get("error", {})]
                else:
                    state["errors"] = state.get("errors", []) + [{"course": "not found"}]
            else:
                state["errors"] = state.get("errors", []) + [search_res.get("error", {})]
        else:
            state["errors"] = state.get("errors", []) + [{"course": "no course specified"}]

    elif intent == "policy":
        res = await client.call_tool("policies_get_current", {"slug": "admissions"})
        if res.get("ok"):
            facts["policy"] = res["data"].get("policy")
        else:
            state["errors"] = state.get("errors", []) + [res.get("error", {})]

    return {**state, "facts": {**state.get("facts", {}), **facts}}


__all__ = ["execute"]