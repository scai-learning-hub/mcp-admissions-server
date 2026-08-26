"""Unit: fee quote validity and version capture (plan §14)."""

from __future__ import annotations

from decimal import Decimal

from tests.helpers import seed_minimal


def test_fee_quote_validity_and_version(memory_db, now_utc):  # noqa: ANN001
    from services.mcp_server.domain.fees import FeeService

    ids = seed_minimal(memory_db)
    svc = FeeService(memory_db)
    result = svc.create_quote(
        actor_id="learner-1",
        course_id=ids["course_id"],
        batch_id=ids["batch_id"],
        currency="INR",
    )
    assert not isinstance(result, tuple), f"Fee quote failed: {result}"
    quote = result
    # Quote stores the exact fee and policy version used when created (plan §8)
    assert quote.policy_version == "1"
    assert quote.source_version == "1"
    assert quote.currency == "INR"
    assert quote.total > Decimal("0")
    # Valid until is in the future
    assert quote.valid_until > now_utc
    # Line items include tuition + GST
    labels = [li.label for li in quote.line_items]
    assert "Tuition" in labels
    assert any("GST" in l for l in labels)


def test_fee_quote_missing_course(memory_db):  # noqa: ANN001
    from packages.contracts.error_codes import ErrorCode
    from services.mcp_server.domain.fees import FeeService

    seed_minimal(memory_db)
    svc = FeeService(memory_db)
    result = svc.create_quote(
        actor_id="learner-1",
        course_id="nonexistent",
        batch_id="any",
        currency="INR",
    )
    assert isinstance(result, tuple)
    code, _ = result
    assert code == ErrorCode.COURSE_NOT_FOUND


def test_fee_quote_batch_mismatch(memory_db):  # noqa: ANN001
    from packages.contracts.error_codes import ErrorCode
    from services.mcp_server.domain.fees import FeeService

    ids = seed_minimal(memory_db)
    svc = FeeService(memory_db)
    result = svc.create_quote(
        actor_id="learner-1",
        course_id=ids["course_id"],
        batch_id="nonexistent-batch",
        currency="INR",
    )
    assert isinstance(result, tuple)
    code, _ = result
    assert code == ErrorCode.BATCH_NOT_AVAILABLE