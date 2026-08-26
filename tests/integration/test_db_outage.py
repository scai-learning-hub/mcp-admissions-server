"""Integration: database outage returns a typed dependency failure (plan §14)."""

from __future__ import annotations

import pytest


async def test_db_outage_returns_typed_failure():  # noqa: ANN001
    from services.mcp_server.auth import Principal, Role
    from services.mcp_server.context import RequestContext
    from services.mcp_server.tools.catalog_tools import catalog_search_courses

    # Point the session factory at an invalid URL to simulate an outage
    import services.mcp_server.repositories.db as db
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    bad_engine = create_engine("postgresql+psycopg://nobody:nobody@localhost:9/admissions",
                               pool_pre_ping=True, future=True)
    db._engine = bad_engine
    db._SessionLocal = sessionmaker(bind=bad_engine, autoflush=False, expire_on_commit=False, future=True)
    ctx = RequestContext(principal=Principal(actor_id="l", role=Role.LEARNER, client_id="t"))
    try:
        res = await catalog_search_courses(ctx, {"query": "x"})
        # Should be a typed failure, not a raw exception
        assert res["ok"] is False
        assert res["error"]["code"] in {"INTERNAL_ERROR", "DEPENDENCY_UNAVAILABLE"}
    finally:
        # Reset the global so other tests aren't affected
        db._engine = None
        db._SessionLocal = None
        bad_engine.dispose()