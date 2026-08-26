"""Unit: payload-hash matching for approval + idempotent writes (plan §14)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from packages.contracts.domain import BatchMode, CallbackWindow
from tests.helpers import seed_minimal


def _make_contact():
    return {
        "name": "Demo Learner",
        "phone": "+919999988910",
        "email": "demo@example.com",
        "timezone": "Asia/Kolkata",
    }


def test_prepare_creates_pending_approval_only(memory_db, now_utc):  # noqa: ANN001
    from services.mcp_server.domain.leads import LeadService

    ids = seed_minimal(memory_db)
    svc = LeadService(memory_db)
    result = svc.prepare_with_approval(
        actor_id="learner-1",
        contact=_make_contact(),
        course_id=ids["course_id"],
        batch_id=ids["batch_id"],
        consent=True,
        consent_at=now_utc,
        requested_callback=None,
    )
    assert not isinstance(result, tuple) or len(result) == 3, result
    approval_id, preview, expires_at = result
    assert approval_id
    assert preview.course_id == ids["course_id"]
    assert preview.contact_summary["phone"].endswith("8910")
    assert expires_at > now_utc

    # Crucially, NO lead row exists yet (plan §16 demo step 6)
    from services.mcp_server.repositories.models import Lead
    assert memory_db.query(Lead).count() == 0


def test_prepare_requires_consent(memory_db, now_utc):  # noqa: ANN001
    from packages.contracts.error_codes import ErrorCode
    from services.mcp_server.domain.leads import LeadService

    ids = seed_minimal(memory_db)
    svc = LeadService(memory_db)
    result = svc.prepare_with_approval(
        actor_id="learner-1",
        contact=_make_contact(),
        course_id=ids["course_id"],
        batch_id=ids["batch_id"],
        consent=False,
        consent_at=now_utc,
    )
    assert isinstance(result, tuple)
    code, _ = result
    assert code == ErrorCode.VALIDATION_FAILED


def test_confirm_create_is_idempotent(memory_db, now_utc):  # noqa: ANN001
    from services.mcp_server.domain.leads import LeadService

    ids = seed_minimal(memory_db)
    svc = LeadService(memory_db)
    prep = svc.prepare_with_approval(
        actor_id="learner-1",
        contact=_make_contact(),
        course_id=ids["course_id"],
        batch_id=ids["batch_id"],
        consent=True,
        consent_at=now_utc,
    )
    approval_id, _, _ = prep
    idem = "idem-" + uuid4().hex[:12]

    r1 = svc.confirm_create(actor_id="learner-1", approval_id=approval_id, idempotency_key=idem)
    assert not isinstance(r1, tuple), r1
    lead_id_1, public_ref_1, _, _ = r1

    # Second call with same idempotency key returns the SAME reference, no duplicate
    # Need a fresh approval because the first was consumed
    prep2 = svc.prepare_with_approval(
        actor_id="learner-1",
        contact=_make_contact(),
        course_id=ids["course_id"],
        batch_id=ids["batch_id"],
        consent=True,
        consent_at=now_utc,
    )
    approval_id_2, _, _ = prep2
    r2 = svc.confirm_create(actor_id="learner-1", approval_id=approval_id_2, idempotency_key=idem)
    assert not isinstance(r2, tuple)
    lead_id_2, public_ref_2, _, _ = r2
    assert lead_id_1 == lead_id_2
    assert public_ref_1 == public_ref_2

    # Only one lead row exists
    from services.mcp_server.repositories.models import Lead
    assert memory_db.query(Lead).count() == 1


def test_expired_approval_rejected(memory_db, now_utc):  # noqa: ANN001
    from packages.contracts.error_codes import ErrorCode
    from services.mcp_server.domain.leads import LeadService

    ids = seed_minimal(memory_db)
    svc = LeadService(memory_db)
    prep = svc.prepare_with_approval(
        actor_id="learner-1",
        contact=_make_contact(),
        course_id=ids["course_id"],
        batch_id=ids["batch_id"],
        consent=True,
        consent_at=now_utc,
    )
    approval_id, _, _ = prep

    # Force expiry
    from services.mcp_server.repositories.models import LeadApproval
    approval = memory_db.get(LeadApproval, approval_id)
    approval.expires_at = now_utc - timedelta(seconds=1)
    memory_db.commit()

    r = svc.confirm_create(actor_id="learner-1", approval_id=approval_id,
                           idempotency_key="idem-expired")
    assert isinstance(r, tuple)
    code, _ = r
    assert code == ErrorCode.APPROVAL_EXPIRED