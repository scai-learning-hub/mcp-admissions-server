"""Batch repository — upcoming batches with seat info."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.mcp_server.repositories.base import BaseRepository
from services.mcp_server.repositories.models import Batch


class BatchRepository(BaseRepository):
    model = Batch

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def find_upcoming(
        self,
        course_id: str,
        *,
        mode: str | None = None,
        now: datetime | None = None,
        limit: int = 5,
    ) -> list[Batch]:
        now = now or datetime.now(timezone.utc)
        stmt = select(Batch).where(
            Batch.course_id == course_id,
            Batch.start_at > now,
            Batch.status.in_(["scheduled", "enrolling"]),
        )
        if mode:
            stmt = stmt.where(Batch.mode == mode)
        stmt = stmt.order_by(Batch.start_at).limit(limit)
        return list(self.session.scalars(stmt))