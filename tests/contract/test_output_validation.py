"""Contract: output validation for every tool (plan §14).

Validates that domain service outputs conform to the typed output models.
"""

from __future__ import annotations

from datetime import datetime, timezone

from packages.contracts.tool_outputs import (
    BatchesFindUpcomingOutput,
    CatalogGetCourseOutput,
    CatalogSearchCoursesOutput,
    FeesCreateQuoteOutput,
    PoliciesGetCurrentOutput,
)
from tests.helpers import seed_minimal


def test_catalog_search_output_shape(memory_db):  # noqa: ANN001
    from services.mcp_server.domain.catalog import CatalogService

    seed_minimal(memory_db)
    svc = CatalogService(memory_db)
    courses = svc.search_courses("agentic")
    out = CatalogSearchCoursesOutput(courses=courses, total=len(courses))
    assert out.total == len(out.courses)


def test_catalog_get_course_output_shape(memory_db):  # noqa: ANN001
    from services.mcp_server.domain.catalog import CatalogService

    ids = seed_minimal(memory_db)
    svc = CatalogService(memory_db)
    course = svc.get_course("agentic-ai")
    out = CatalogGetCourseOutput(course=course)
    assert out.course.slug == "agentic-ai"


def test_batches_output_shape(memory_db):  # noqa: ANN001
    from services.mcp_server.domain.catalog import CatalogService

    ids = seed_minimal(memory_db)
    svc = CatalogService(memory_db)
    batches = svc.find_upcoming_batches(ids["course_id"])
    out = BatchesFindUpcomingOutput(batches=batches)
    assert len(out.batches) >= 1
    assert out.batches[0].seats.seats_available >= 0


def test_fee_quote_output_shape(memory_db):  # noqa: ANN001
    from services.mcp_server.domain.fees import FeeService

    ids = seed_minimal(memory_db)
    svc = FeeService(memory_db)
    quote = svc.create_quote(actor_id="l1", course_id=ids["course_id"], batch_id=ids["batch_id"])
    assert not isinstance(quote, tuple)
    out = FeesCreateQuoteOutput(quote=quote)
    assert out.quote.quote_id
    assert out.quote.total > 0


def test_policy_output_shape(memory_db):  # noqa: ANN001
    from services.mcp_server.domain.policies import PolicyService

    seed_minimal(memory_db)
    svc = PolicyService(memory_db)
    p = svc.get_current("admissions")
    out = PoliciesGetCurrentOutput(policy=p)
    assert out.policy.slug == "admissions"
    assert "Admissions" in out.policy.content_md