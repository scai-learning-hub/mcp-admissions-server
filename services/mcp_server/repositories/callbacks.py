"""Callback repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.mcp_server.repositories.base import BaseRepository
from services.mcp_server.repositories.models import Callback


class CallbackRepository(BaseRepository):
    model = Callback

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def create(self, callback: Callback) -> Callback:
        self.session.add(callback)
        self.session.flush()
        return callback

    def list_for_lead(self, lead_id: str) -> list[Callback]:
        stmt = select(Callback).where(Callback.lead_id == lead_id).order_by(Callback.created_at.desc())
        return list(self.session.scalars(stmt))