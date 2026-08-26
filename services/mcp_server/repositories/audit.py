"""Audit repository — append-only tool audit events."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.mcp_server.repositories.base import BaseRepository
from services.mcp_server.repositories.models import ToolAuditEvent


class AuditRepository(BaseRepository):
    model = ToolAuditEvent

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def append(self, event: ToolAuditEvent) -> ToolAuditEvent:
        self.session.add(event)
        self.session.flush()
        return event

    def list_recent(self, *, limit: int = 50) -> list[ToolAuditEvent]:
        stmt = select(ToolAuditEvent).order_by(ToolAuditEvent.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt))

    def list_by_trace(self, trace_id: str) -> list[ToolAuditEvent]:
        stmt = (
            select(ToolAuditEvent)
            .where(ToolAuditEvent.trace_id == trace_id)
            .order_by(ToolAuditEvent.created_at)
        )
        return list(self.session.scalars(stmt))