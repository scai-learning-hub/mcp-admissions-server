"""Node: discover — list MCP tools (separate from learner host's discovery)."""

from __future__ import annotations

from services.counsellor_host.client_registry import get_client
from services.counsellor_host.state import CounsellorState


async def discover_capabilities(state: CounsellorState) -> CounsellorState:
    client = get_client(state.get("thread_id", ""))
    if client is None:
        return {**state, "discovered_tools": [],
                "errors": state.get("errors", []) + [{"discover": "no client"}]}
    try:
        tools = await client.list_tools()
    except Exception as e:
        return {**state, "discovered_tools": [],
                "errors": state.get("errors", []) + [{"discover": str(e)}]}
    return {**state, "discovered_tools": tools}


__all__ = ["discover_capabilities"]