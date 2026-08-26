"""Node: execute_reads — call bounded read tools and collect typed results."""

from __future__ import annotations

from services.learner_host.client_registry import get_client
from services.learner_host.state import LearnerState


async def execute_reads(state: LearnerState) -> LearnerState:
    client = get_client(state.get("thread_id", ""))
    if client is None:
        return {**state, "errors": state.get("errors", []) + [{"reads": "no client"}]}
    facts: dict = {}
    course_slug = state.get("requested_course")

    if course_slug:
        # Specific course requested — fetch full details
        res = await client.call_tool("catalog_search_courses", {"query": course_slug})
        if res.get("ok"):
            courses = res["data"].get("courses", [])
            facts["courses"] = courses
            if courses:
                course_id = courses[0]["id"]
                facts["course_id"] = course_id
                facts["course_title"] = courses[0]["title"]
                # 2. batches
                batches_res = await client.call_tool(
                    "batches_find_upcoming",
                    {"course_id": course_id, "mode": state.get("requested_mode"),
                     "timezone": state.get("timezone", "UTC")},
                )
                if batches_res.get("ok"):
                    facts["batches"] = batches_res["data"].get("batches", [])
                    if facts["batches"]:
                        facts["batch_id"] = facts["batches"][0]["id"]
                        facts["batch_start"] = facts["batches"][0]["start_at"]
                        # 3. fee quote
                        quote_res = await client.call_tool(
                            "fees_create_quote",
                            {"course_id": course_id, "batch_id": facts["batch_id"]},
                        )
                        if quote_res.get("ok"):
                            facts["quote"] = quote_res["data"].get("quote")
                        else:
                            facts["quote_error"] = quote_res.get("error", {})
                else:
                    facts["batches_error"] = batches_res.get("error", {})
            # 4. policy
            pol_res = await client.call_tool("policies_get_current", {"slug": "admissions"})
            if pol_res.get("ok"):
                facts["policy"] = pol_res["data"].get("policy")
            else:
                facts["policy_error"] = pol_res.get("error", {})
        else:
            facts["courses_error"] = res.get("error", {})
    else:
        # General catalogue search — no specific course requested
        res = await client.call_tool("catalog_search_courses", {"query": "a"})
        if res.get("ok"):
            facts["courses"] = res["data"].get("courses", [])
        else:
            facts["courses_error"] = res.get("error", {})

    # Policy intent — fetch the admissions policy directly
    if state.get("intent") == "policy" or state.get("facts", {}).get("needs", []) and "policy" in state.get("facts", {}).get("needs", []) and not course_slug:
        pol_res = await client.call_tool("policies_get_current", {"slug": "admissions"})
        if pol_res.get("ok"):
            facts["policy"] = pol_res["data"].get("policy")
        else:
            facts["policy_error"] = pol_res.get("error", {})

    return {**state, "facts": {**state.get("facts", {}), **facts}}


__all__ = ["execute_reads"]