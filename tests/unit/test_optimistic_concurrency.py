"""Unit: optimistic concurrency for stage updates (plan §14)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from tests.helpers import seed_minimal


def _create_lead(memory_db, ids):  # noqa: ANN001
    from services.mcp_server.domain.leads import LeadService

    svc = LeadService(memory_db)
    prep = svc.prepare_with_approval(
        actor_id="counsellor-1",
        contact={"name": "L", "phone": "+919999988910", "email": "l@example.com", "timezone": "UTC"},
        course_id=ids["course_id"],
        batch_id=ids["batch_id"],
        consent=True,
        consent_at=datetime.now(timezone.utc),
    )
    approval_id, _, _ = prep
    r = svc.confirm_create(actor_id="learner-1", approval_id=approval_id,
                           idempotency_key="idem-" + uuid4().hex[:8])
    lead_id, _, _, _ = r
    # Assign to counsellor-1
    from services.mcp_server.repositories.models import Lead

    lead = memory_db.get(Lead, lead_id)
    lead.assigned_to = "counsellor-1"
    memory_db.commit()
    return lead_id, lead.row_version


def test_stage_update_success(memory_db):  # noqa: ANN001
    from services.mcp_server.domain.leads import LeadService

    ids = seed_minimal(memory_db)
    lead_id, version = _create_lead(memory_db, ids)
    svc = LeadService(memory_db)
    r = svc.update_stage(
        lead_id=lead_id, expected_version=version, new_stage="contacted",
        note="Called", actor_id="counsellor-1", idempotency_key="u1",
        counsellor_id="counsellor-1",
    )
    assert not isinstance(r, tuple)
    _, stage, new_version = r
    assert stage == "contacted"
    assert new_version == version + 1


def test_stage_update_version_conflict(memory_db):  # noqa: ANN001
    from packages.contracts.error_codes import ErrorCode
    from services.mcp_server.domain.leads import LeadService

    ids = seed_minimal(memory_db)
    lead_id, version = _create_lead(memory_db, ids)
    svc = LeadService(memory_db)
    # First update succeeds, bumping version
    svc.update_stage(
        lead_id=lead_id, expected_version=version, new_stage="contacted",
        note="1", actor_id="counsellor-1", idempotency_key="u1",
        counsellor_id="counsellor-1",
    )
    # Second update with STALE version must fail with VERSION_CONFLICT
    r = svc.update_stage(
        lead_id=lead_id, expected_version=version, new_stage="qualified",
        note="2", actor_id="counsellor-1", idempotency_key="u2",
        counsellor_id="counsellor-1",
    )
    assert isinstance(r, tuple)
    code, _ = r
    assert code == ErrorCode.VERSION_CONFLICT


def test_stage_update_unassigned_counsellor_forbidden(memory_db):  # noqa: ANN001
    from packages.contracts.error_codes import ErrorCode
    from services.mcp_server.domain.leads import LeadService

    ids = seed_minimal(memory_db)
    lead_id, version = _create_lead(memory_db, ids)
    svc = LeadService(memory_db)
    r = svc.update_stage(
        lead_id=lead_id, expected_version=version, new_stage="contacted",
        note="x", actor_id="counsellor-OTHER", idempotency_key="u-other",
        counsellor_id="counsellor-OTHER",
    )
    assert isinstance(r, tuple)
    code, _ = r
    assert code == ErrorCode.FORBIDDEN