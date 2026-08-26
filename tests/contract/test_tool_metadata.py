"""Contract: tool metadata read/write correctness (plan §14)."""

from __future__ import annotations

from services.mcp_server.tools._runner import ROLE_TOOLS
from services.mcp_server.auth import Role


def test_read_tools_available_to_learner():
    reads = {"catalog.search_courses", "catalog.get_course", "batches.find_upcoming",
             "fees.create_quote", "policies.get_current"}
    assert reads.issubset(ROLE_TOOLS[Role.LEARNER])


def test_write_tools_available_to_learner():
    writes = {"leads.prepare", "leads.confirm_create", "callbacks.schedule"}
    assert writes.issubset(ROLE_TOOLS[Role.LEARNER])


def test_counsellor_has_lead_read_update_but_not_learner_writes():
    c = ROLE_TOOLS[Role.COUNSELLOR]
    assert "leads.list_assigned" in c
    assert "leads.get_summary" in c
    assert "leads.update_stage" in c
    # Counsellor does NOT create leads via MCP
    assert "leads.confirm_create" not in c


def test_auditor_has_no_business_tools():
    assert ROLE_TOOLS[Role.AUDITOR] == set()