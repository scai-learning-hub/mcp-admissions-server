"""Node: execute_write — perform the confirmed stage update."""

from __future__ import annotations

from uuid import uuid4

from services.counsellor_host.client_registry import get_client
from services.counsellor_host.state import CounsellorState


async def execute_write(state: CounsellorState) -> CounsellorState:
    if not state.get("confirmed"):
        return state
    if state.get("pending_action") != "update_stage":
        return state

    client = get_client(state.get("thread_id", ""))
    if client is None:
        return {**state, "errors": state.get("errors", []) + [{"execute": "no client"}]}
    lead_id = state.get("target_lead_id")
    new_stage = state.get("new_stage")
    lead = state.get("facts", {}).get("current_lead", {})
    expected_version = lead.get("row_version", 1) if isinstance(lead, dict) else 1

    res = await client.call_tool("leads_update_stage", {
        "lead_id": lead_id,
        "expected_version": expected_version,
        "new_stage": new_stage,
        "note": f"Updated via counsellor chat",
        "idempotency_key": f"chat-{uuid4().hex[:12]}",
    })
    if res.get("ok"):
        state["tool_results"] = {"stage_update": res["data"]}
    else:
        state["errors"] = state.get("errors", []) + [res.get("error", {})]
    return state


__all__ = ["execute_write"]