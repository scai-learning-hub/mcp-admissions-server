"""Node: discover_capabilities — cache the current server capability list."""

from __future__ import annotations

from services.learner_host.client_registry import get_client
from services.learner_host.state import LearnerState


async def discover_capabilities(state: LearnerState) -> LearnerState:
    client = get_client(state.get("thread_id", ""))
    if client is None:
        return {**state, "discovered_tools": [], "errors": state.get("errors", []) + [{"discover": "no client"}]}
    try:
        tools = await client.list_tools()
    except Exception as e:
        return {**state, "discovered_tools": [], "errors": state.get("errors", []) + [{"discover": str(e)}]}
    return {**state, "discovered_tools": tools}


__all__ = ["discover_capabilities"]