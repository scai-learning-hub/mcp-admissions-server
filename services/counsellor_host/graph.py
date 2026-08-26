"""Counsellor host graph — separate from learner host graph.

flow:
  receive → normalize → discover → execute
    → write needed? → (no) → compose
    → (yes) → await_confirmation → (no) → compose
                           → (yes) → execute_write → compose
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from services.counsellor_host.nodes.await_confirmation import await_confirmation
from services.counsellor_host.nodes.compose_response import compose_response
from services.counsellor_host.nodes.discover_capabilities import discover_capabilities
from services.counsellor_host.nodes.execute import execute
from services.counsellor_host.nodes.execute_write import execute_write
from services.counsellor_host.nodes.normalize_request import normalize_request
from services.counsellor_host.state import CounsellorState


def _after_execute(state: CounsellorState) -> str:
    if state.get("errors"):
        return "compose"
    if state.get("pending_action") == "update_stage":
        return "confirm"
    return "compose"


def _after_confirmation(state: CounsellorState) -> str:
    if state.get("confirmed"):
        return "execute_write"
    return "compose"


def build_graph():
    g = StateGraph(CounsellorState)
    g.add_node("normalize_request", normalize_request)
    g.add_node("discover_capabilities", discover_capabilities)
    g.add_node("execute", execute)
    g.add_node("await_confirmation", await_confirmation)
    g.add_node("execute_write", execute_write)
    g.add_node("compose_response", compose_response)

    g.set_entry_point("normalize_request")
    g.add_edge("normalize_request", "discover_capabilities")
    g.add_edge("discover_capabilities", "execute")
    g.add_conditional_edges("execute", _after_execute, {
        "confirm": "await_confirmation",
        "compose": "compose_response",
    })
    g.add_conditional_edges("await_confirmation", _after_confirmation, {
        "execute_write": "execute_write",
        "compose": "compose_response",
    })
    g.add_edge("execute_write", "compose_response")
    g.add_edge("compose_response", END)

    return g.compile(checkpointer=MemorySaver())


counsellor_graph = build_graph()


__all__ = ["build_graph", "counsellor_graph"]