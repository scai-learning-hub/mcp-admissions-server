"""Shared pytest fixtures.

Integration tests use an in-memory SQLite DB by default (fast, no Docker).
PostgreSQL-specific JSONB is mapped to plain JSON on SQLite via a compile hook.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


# Make JSONB compile as TEXT/JSON on non-postgres dialects (for sqlite tests)
@compiles(JSONB, "sqlite")
def _jsonb_to_sqlite(element, compiler, **kw):  # noqa: ARG001
    return "JSON"


@pytest.fixture()
def memory_db() -> Session:
    """An in-memory SQLite session with all tables created."""
    from services.mcp_server.repositories.models import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    sm = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    sess = sm()
    try:
        yield sess
    finally:
        sess.close()
        engine.dispose()


@pytest.fixture()
def now_utc() -> datetime:
    return datetime.now(timezone.utc)