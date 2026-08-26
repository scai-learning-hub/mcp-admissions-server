"""Integration: tool → domain service → DB (plan §14)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from packages.contracts.domain import BatchMode
from tests.helpers import seed_minimal


def _ctx(role, actor="learner-1"):
    from services.mcp_server.auth import Principal, Role
    from services.mcp_server.context import RequestContext

    return RequestContext(principal=Principal(actor_id=actor, role=Role.LEARNER, client_id="test"))


async def test_tool_to_db_read(memory_db):  # noqa: ANN001
    from services.mcp_server.tools.catalog_tools import catalog_search_courses

    seed_minimal(memory_db)
    # Patch the session factory to use our in-memory session
    _patch_session(memory_db)
    ctx = _ctx("learner-1")
    res = await catalog_search_courses(ctx, {"query": "agentic", "limit": 5})
    assert res["ok"] is True
    assert any(c["slug"] == "agentic-ai" for c in res["data"]["courses"])


async def test_tool_to_db_fee_quote(memory_db):  # noqa: ANN001
    from services.mcp_server.tools.fee_tools import fees_create_quote

    ids = seed_minimal(memory_db)
    _patch_session(memory_db)
    ctx = _ctx("learner-1")
    res = await fees_create_quote(ctx, {
        "course_id": ids["course_id"], "batch_id": ids["batch_id"], "currency": "INR",
    })
    assert res["ok"] is True
    assert res["data"]["quote"]["policy_version"] == "1"


async def test_duplicate_idempotency_returns_same_reference(memory_db):  # noqa: ANN001
    from services.mcp_server.tools.lead_tools import leads_confirm_create, leads_prepare

    ids = seed_minimal(memory_db)
    _patch_session(memory_db)
    ctx = _ctx("learner-1")
    now = datetime.now(timezone.utc).isoformat()

    prep = await leads_prepare(ctx, {
        "contact": {"name": "L", "phone": "+919999988910", "email": "l@example.com", "timezone": "UTC"},
        "course_id": ids["course_id"], "batch_id": ids["batch_id"], "consent": True,
        "consent_at": now, "requested_callback": None,
    })
    assert prep["ok"]
    approval_id = prep["data"]["approval_id"]
    idem = "idem-" + uuid4().hex[:12]

    r1 = await leads_confirm_create(ctx, {"approval_id": approval_id, "idempotency_key": idem})
    assert r1["ok"]
    ref1 = r1["data"]["public_reference"]

    # Prepare a second approval and try the SAME idempotency key
    prep2 = await leads_prepare(ctx, {
        "contact": {"name": "L", "phone": "+919999988910", "email": "l@example.com", "timezone": "UTC"},
        "course_id": ids["course_id"], "batch_id": ids["batch_id"], "consent": True,
        "consent_at": now, "requested_callback": None,
    })
    r2 = await leads_confirm_create(ctx, {
        "approval_id": prep2["data"]["approval_id"], "idempotency_key": idem,
    })
    assert r2["ok"]
    assert r2["data"]["public_reference"] == ref1


async def test_concurrent_stage_update_returns_version_conflict(memory_db):  # noqa: ANN001
    from services.mcp_server.tools.lead_tools import leads_confirm_create, leads_prepare, leads_update_stage

    ids = seed_minimal(memory_db)
    _patch_session(memory_db)
    ctx = _ctx("learner-1")
    now = datetime.now(timezone.utc).isoformat()

    prep = await leads_prepare(ctx, {
        "contact": {"name": "L", "phone": "+919999988910", "email": "l@example.com", "timezone": "UTC"},
        "course_id": ids["course_id"], "batch_id": ids["batch_id"], "consent": True,
        "consent_at": now, "requested_callback": None,
    })
    r = await leads_confirm_create(ctx, {
        "approval_id": prep["data"]["approval_id"], "idempotency_key": "idem-c-" + uuid4().hex[:6],
    })
    lead_id = r["data"]["lead_id"]

    # Assign to counsellor
    from services.mcp_server.repositories.models import Lead

    lead = memory_db.get(Lead, lead_id)
    lead.assigned_to = "learner-1"  # use the ctx actor so scope checks pass
    memory_db.commit()

    # First update
    u1 = await leads_update_stage(ctx, {
        "lead_id": lead_id, "expected_version": 1, "new_stage": "contacted",
        "note": "1", "idempotency_key": "u1",
    })
    assert u1["ok"]
    # Second with stale version
    u2 = await leads_update_stage(ctx, {
        "lead_id": lead_id, "expected_version": 1, "new_stage": "qualified",
        "note": "2", "idempotency_key": "u2",
    })
    assert u2["ok"] is False
    assert u2["error"]["code"] == "VERSION_CONFLICT"


async def test_audit_event_recorded(memory_db):  # noqa: ANN001
    from services.mcp_server.tools.catalog_tools import catalog_search_courses

    seed_minimal(memory_db)
    _patch_session(memory_db)
    ctx = _ctx("learner-1")
    await catalog_search_courses(ctx, {"query": "agentic"})
    # The runner appends audit events in a NEW session, so they land in the same
    # in-memory DB. Verify at least one audit row exists.
    from services.mcp_server.repositories.models import ToolAuditEvent
    rows = memory_db.query(ToolAuditEvent).all()
    assert len(rows) >= 1
    assert rows[0].tool_name == "catalog.search_courses"
    assert rows[0].actor_id == "learner-1"


# ---------------------------------------------------------------------------
# Helper: point the session factory at our in-memory engine for the test
# ---------------------------------------------------------------------------


def _patch_session(memory_db) -> None:
    import services.mcp_server.repositories.db as db

    # Reuse the same engine bound to memory_db
    engine = memory_db.get_bind()
    from sqlalchemy.orm import sessionmaker

    sm = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    db._engine = engine
    db._SessionLocal = sm