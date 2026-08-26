"""Unit: batch filtering across timezone and mode (plan §14)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from packages.contracts.domain import BatchMode
from tests.helpers import seed_minimal


def test_find_upcoming_batches(memory_db):  # noqa: ANN001
    from services.mcp_server.domain.catalog import CatalogService

    ids = seed_minimal(memory_db)
    svc = CatalogService(memory_db)
    batches = svc.find_upcoming_batches(ids["course_id"], limit=10)
    assert len(batches) == 1
    assert batches[0].mode == BatchMode.ONLINE
    assert batches[0].seats.seats_available == 15


def test_find_upcoming_filtered_by_mode(memory_db):  # noqa: ANN001
    from services.mcp_server.domain.catalog import CatalogService
    from services.mcp_server.repositories.models import Batch

    ids = seed_minimal(memory_db)
    # Add a hybrid batch
    memory_db.add(Batch(
        course_id=ids["course_id"],
        start_at=datetime.now(timezone.utc) + timedelta(days=20),
        timezone="UTC",
        mode="hybrid",
        seats_total=10,
        seats_reserved=0,
        status="enrolling",
    ))
    memory_db.commit()

    svc = CatalogService(memory_db)
    online = svc.find_upcoming_batches(ids["course_id"], mode=BatchMode.ONLINE)
    hybrid = svc.find_upcoming_batches(ids["course_id"], mode=BatchMode.HYBRID)
    assert all(b.mode == BatchMode.ONLINE for b in online)
    assert all(b.mode == BatchMode.HYBRID for b in hybrid)
    assert len(online) == 1
    assert len(hybrid) == 1


def test_find_upcoming_excludes_past_batches(memory_db):  # noqa: ANN001
    from services.mcp_server.domain.catalog import CatalogService
    from services.mcp_server.repositories.models import Batch

    ids = seed_minimal(memory_db)
    memory_db.add(Batch(
        course_id=ids["course_id"],
        start_at=datetime.now(timezone.utc) - timedelta(days=1),  # past
        timezone="UTC",
        mode="online",
        seats_total=10,
        seats_reserved=0,
        status="started",
    ))
    memory_db.commit()

    svc = CatalogService(memory_db)
    batches = svc.find_upcoming_batches(ids["course_id"])
    assert all(b.start_at > datetime.now(timezone.utc) for b in batches)
    assert len(batches) == 1  # only the future one from seed_minimal