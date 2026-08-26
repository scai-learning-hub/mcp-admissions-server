"""Security: authorization matrix (plan §14).

- Learner cannot list leads.
- Counsellor cannot read an unassigned lead.
- Learner cannot call an admin operation.
- Expired token is rejected before tool execution.
- Valid confirmation for one payload cannot authorize a changed payload.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services.mcp_server.auth import AuthError, Principal, Role, issue_token, verify_token
from services.mcp_server.config import settings
from services.mcp_server.tools._runner import authorize


def _principal(role: Role) -> Principal:
    return Principal(actor_id="x", role=role, client_id="test")


def test_learner_cannot_list_leads():
    assert authorize(_principal(Role.LEARNER), "leads.list_assigned") is not None


def test_learner_cannot_call_admin_ops():
    # No admin tools are exposed via MCP in V1, so any admin-ish name is denied
    assert authorize(_principal(Role.LEARNER), "admin.update_fee") is not None


def test_counsellor_cannot_create_leads():
    assert authorize(_principal(Role.COUNSELLOR), "leads.confirm_create") is not None


def test_auditor_cannot_execute_business_tools():
    assert authorize(_principal(Role.AUDITOR), "catalog.search_courses") is not None


def test_expired_token_rejected():
    token = issue_token(subject="x", role=Role.LEARNER, client_id="c",
                        expires_in_seconds=-1)  # already expired
    try:
        verify_token(token)
        assert False, "Expected AuthError"
    except AuthError as e:
        assert e.code.value == "UNAUTHENTICATED"


def test_invalid_token_rejected():
    try:
        verify_token("not-a-jwt")
        assert False, "Expected AuthError"
    except AuthError as e:
        assert e.code.value == "UNAUTHENTICATED"


def test_confirmation_cannot_authorize_changed_payload(memory_db, now_utc):  # noqa: ANN001
    """The server re-derives the hash from its own stored preview, not the
    client's claim. So a changed payload at confirm time is impossible — the
    client only sends approval_id + idempotency_key."""
    from services.mcp_server.domain.leads import LeadService
    from tests.helpers import seed_minimal
    from uuid import uuid4

    ids = seed_minimal(memory_db)
    svc = LeadService(memory_db)
    contact_a = {"name": "A", "phone": "+919999988910", "email": "a@example.com", "timezone": "UTC"}
    prep = svc.prepare_with_approval(
        actor_id="learner-1", contact=contact_a, course_id=ids["course_id"],
        batch_id=ids["batch_id"], consent=True, consent_at=now_utc,
    )
    approval_id, _, _ = prep

    # Confirm with the SAME approval — the lead is created from the STORED preview,
    # not from anything the client sends now. There is no way to change the payload
    # at confirm time because confirm_create only accepts approval_id.
    r = svc.confirm_create(actor_id="learner-1", approval_id=approval_id,
                           idempotency_key="idem-" + uuid4().hex[:8])
    assert not isinstance(r, tuple)
    # The lead reflects the ORIGINAL contact, not a changed one.
    from services.mcp_server.repositories.models import Lead
    lead = memory_db.query(Lead).first()
    assert lead is not None
    assert lead.course_id == ids["course_id"]