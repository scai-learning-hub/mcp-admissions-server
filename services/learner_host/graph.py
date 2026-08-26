"""LangGraph graph definition (plan §9).

flowchart:
  receive → normalize → plan → discover → execute_reads
    → write requested? → (no) → compose
    → (yes) → prepare → await_confirmation → (no) → compose
                                    → (yes) → execute_write → verify → compose

The host must never claim "callback booked" from model text alone.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from services.learner_host.nodes.await_confirmation import await_confirmation
from services.learner_host.nodes.compose_response import compose_response
from services.learner_host.nodes.discover_capabilities import discover_capabilities
from services.learner_host.nodes.execute_reads import execute_reads
from services.learner_host.nodes.execute_write import execute_write
from services.learner_host.nodes.handle_failure import handle_failure
from services.learner_host.nodes.normalize_request import normalize_request
from services.learner_host.nodes.plan_facts import plan_facts
from services.learner_host.nodes.prepare_write import prepare_write
from services.learner_host.nodes.verify_state import verify_state
from services.learner_host.state import LearnerState


def _after_reads(state: LearnerState) -> str:
    if state.get("errors"):
        return "handle_failure"
    needs = state.get("facts", {}).get("needs", [])
    if "lead_prepare" in needs:
        return "prepare"
    return "compose"


def _after_confirmation(state: LearnerState) -> str:
    if state.get("confirmed"):
        return "execute_write"
    return "compose"


def build_graph():
    g = StateGraph(LearnerState)
    g.add_node("normalize_request", normalize_request)
    g.add_node("plan_facts", plan_facts)
    g.add_node("discover_capabilities", discover_capabilities)
    g.add_node("execute_reads", execute_reads)
    g.add_node("prepare_write", prepare_write)
    g.add_node("await_confirmation", await_confirmation)
    g.add_node("execute_write", execute_write)
    g.add_node("verify_state", verify_state)
    g.add_node("compose_response", compose_response)
    g.add_node("handle_failure", handle_failure)

    g.set_entry_point("normalize_request")
    g.add_edge("normalize_request", "plan_facts")
    g.add_edge("plan_facts", "discover_capabilities")
    g.add_edge("discover_capabilities", "execute_reads")
    g.add_conditional_edges("execute_reads", _after_reads, {
        "handle_failure": "handle_failure",
        "prepare": "prepare_write",
        "compose": "compose_response",
    })
    g.add_edge("prepare_write", "await_confirmation")
    g.add_conditional_edges("await_confirmation", _after_confirmation, {
        "execute_write": "execute_write",
        "compose": "compose_response",
    })
    g.add_edge("execute_write", "verify_state")
    g.add_edge("verify_state", "compose_response")
    g.add_edge("handle_failure", END)
    g.add_edge("compose_response", END)

    return g.compile(checkpointer=MemorySaver())


# Compiled graph singleton
learner_graph = build_graph()


__all__ = ["build_graph", "learner_graph"]