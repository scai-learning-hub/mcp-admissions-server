"""Contract: tool input schema rejection for malformed arguments (plan §14)."""

from __future__ import annotations

import pytest

from packages.contracts.tool_inputs import (
    CatalogSearchCoursesInput,
    LeadsConfirmCreateInput,
    LeadsPrepareInput,
)


def test_search_courses_rejects_empty_query():
    with pytest.raises(Exception):
        CatalogSearchCoursesInput(query="")


def test_search_courses_rejects_oversized_limit():
    with pytest.raises(Exception):
        CatalogSearchCoursesInput(query="ai", limit=999)


def test_confirm_create_requires_idempotency_key_min_length():
    with pytest.raises(Exception):
        LeadsConfirmCreateInput(approval_id="x", idempotency_key="ab")  # <4


def test_leads_prepare_requires_consent_field():
    # Missing consent should fail validation
    with pytest.raises(Exception):
        LeadsPrepareInput(
            contact={"name": "X", "phone": "+910000000000", "email": "x@y.com", "timezone": "UTC"},
            course_id="c", batch_id="b", consent_at="2026-01-01T00:00:00Z",
        )