"""Idempotency repository — actor+tool+key uniqueness."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.mcp_server.repositories.base import BaseRepository
from services.mcp_server.repositories.models import IdempotencyRecord


class IdempotencyRepository(BaseRepository):
    model = IdempotencyRecord

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def find(
        self,
        *,
        actor_id: str,
        tool_name: str,
        idempotency_key: str,
    ) -> IdempotencyRecord | None:
        stmt = select(IdempotencyRecord).where(
            IdempotencyRecord.actor_id == actor_id,
            IdempotencyRecord.tool_name == tool_name,
            IdempotencyRecord.idempotency_key == idempotency_key,
        )
        return self.session.scalars(stmt).first()

    def create(self, record: IdempotencyRecord) -> IdempotencyRecord:
        self.session.add(record)
        self.session.flush()
        return record