"""Contract: resource URI resolution and prompt metadata (plan §14)."""

from __future__ import annotations


def test_resource_schemas_present():
    from services.mcp_server.resources import schema_fee_quote, schema_lead_intake

    s_lead = schema_lead_intake()
    s_quote = schema_fee_quote()
    assert "properties" in s_lead
    assert "properties" in s_quote


def test_prompt_versions():
    from services.mcp_server.prompts import (
        PROMPT_VERSION,
        admissions_qualify_enquiry,
        counsellor_prepare_callback,
    )

    p1 = admissions_qualify_enquiry("agentic ai", "beginner", "weekends")
    p2 = counsellor_prepare_callback("SCAI-1234")
    assert p1["version"] == PROMPT_VERSION
    assert p2["version"] == PROMPT_VERSION
    assert "agentic ai" in p1["template"]
    assert "SCAI-1234" in p2["template"]