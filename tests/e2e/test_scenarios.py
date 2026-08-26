"""End-to-end scenarios (plan §14) run against in-memory DB via tools layer.

These prove the business scenarios without requiring a running HTTP server:
they drive the graph/tools directly. The HTTP e2e (run_demo_checks.py) covers
the live server path.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from tests.helpers import seed_minimal


def _ctx(role="learner", actor="learner-1"):
    from services.mcp_server.auth import Principal, Role
    from services.mcp_server.context import RequestContext

    return RequestContext(principal=Principal(
        actor_id=actor, role=Role(role), client_id="e2e"))


def _patch(memory_db):  # noqa: ANN001
    import services.mcp_server.repositories.db as db
    from sqlalchemy.orm import sessionmaker

    engine = memory_db.get_bind()
    db._engine = engine
    db._SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


async def test_course_and_batch_enquiry_cites_live_records(memory_db):  # noqa: ANN001
    from services.mcp_server.tools.batch_tools import batches_find_upcoming
    from services.mcp_server.tools.catalog_tools import catalog_search_courses

    seed_minimal(memory_db)
    _patch(memory_db)
    ctx = _ctx()
    courses = await catalog_search_courses(ctx, {"query": "agentic"})
    assert courses["ok"]
    course_id = courses["data"]["courses"][0]["id"]

    batches = await batches_find_upcoming(ctx, {"course_id": course_id, "mode": "online"})
    assert batches["ok"]
    assert len(batches["data"]["batches"]) >= 1
    # Answer cites current records returned through MCP
    assert batches["data"]["batches"][0]["course_id"] == course_id


async def test_fee_enquiry_includes_id_amount_validity_source_version(memory_db):  # noqa: ANN001
    from services.mcp_server.tools.fee_tools import fees_create_quote

    ids = seed_minimal(memory_db)
    _patch(memory_db)
    ctx = _ctx()
    res = await fees_create_quote(ctx, {
        "course_id": ids["course_id"], "batch_id": ids["batch_id"],
    })
    q = res["data"]["quote"]
    assert q["quote_id"]
    assert q["total"]
    assert q["valid_until"]
    assert q["source_version"] == "1"


async def test_callback_request_without_confirmation_writes_nothing(memory_db):  # noqa: ANN001
    from services.mcp_server.tools.lead_tools import leads_prepare

    ids = seed_minimal(memory_db)
    _patch(memory_db)
    ctx = _ctx()
    prep = await leads_prepare(ctx, {
        "contact": {"name": "L", "phone": "+919999988910", "email": "l@example.com", "timezone": "UTC"},
        "course_id": ids["course_id"], "batch_id": ids["batch_id"], "consent": True,
        "consent_at": datetime.now(timezone.utc).isoformat(),
    })
    assert prep["ok"]
    # No lead row yet
    from services.mcp_server.repositories.models import Lead
    assert memory_db.query(Lead).count() == 0


async def test_confirmed_callback_request_creates_lead_and_callback(memory_db):  # noqa: ANN001
    from services.mcp_server.tools.callback_tools import callbacks_schedule
    from services.mcp_server.tools.lead_tools import leads_confirm_create, leads_prepare

    ids = seed_minimal(memory_db)
    _patch(memory_db)
    ctx = _ctx()
    now = datetime.now(timezone.utc).isoformat()
    prep = await leads_prepare(ctx, {
        "contact": {"name": "L", "phone": "+919999988910", "email": "l@example.com", "timezone": "UTC"},
        "course_id": ids["course_id"], "batch_id": ids["batch_id"], "consent": True,
        "consent_at": now,
    })
    approval_id = prep["data"]["approval_id"]
    idem = "idem-" + uuid4().hex[:12]
    r = await leads_confirm_create(ctx, {"approval_id": approval_id, "idempotency_key": idem})
    assert r["ok"]
    lead_id = r["data"]["lead_id"]

    # Schedule callback using a fresh approval (prepare again for callback)
    prep2 = await leads_prepare(ctx, {
        "contact": {"name": "L", "phone": "+919999988910", "email": "l@example.com", "timezone": "UTC"},
        "course_id": ids["course_id"], "batch_id": ids["batch_id"], "consent": True,
        "consent_at": now,
    })
    cb = await callbacks_schedule(ctx, {
        "lead_id": lead_id,
        "window": {"start_at": now, "end_at": now, "timezone": "UTC"},
        "approval_id": prep2["data"]["approval_id"],
        "idempotency_key": "cb-" + idem,
    })
    assert cb["ok"]
    assert cb["data"]["callback"]["callback_id"]


async def test_unauthorized_lead_lookup_denied_and_audited(memory_db):  # noqa: ANN001
    from services.mcp_server.tools.lead_tools import leads_list_assigned

    seed_minimal(memory_db)
    _patch(memory_db)
    # Learner tries to list leads -> FORBIDDEN
    ctx = _ctx(role="learner", actor="learner-1")
    res = await leads_list_assigned(ctx, {"limit": 5})
    assert res["ok"] is False
    assert res["error"]["code"] == "FORBIDDEN"
    # And an audit event was recorded for the denial
    from services.mcp_server.repositories.models import ToolAuditEvent
    audit = memory_db.query(ToolAuditEvent).filter(
        ToolAuditEvent.tool_name == "leads.list_assigned"
    ).all()
    assert any(a.result_code == "FORBIDDEN" for a in audit)


async def test_second_client_reuses_same_endpoint(memory_db):  # noqa: ANN001
    """Counsellor client reuses the same MCP tool surface (plan §14 e2e)."""
    from services.mcp_server.tools.lead_tools import leads_list_assigned

    seed_minimal(memory_db)
    _patch(memory_db)
    ctx = _ctx(role="counsellor", actor="counsellor-1")
    res = await leads_list_assigned(ctx, {"limit": 5})
    assert res["ok"]  # empty list is fine; the point is it was authorized