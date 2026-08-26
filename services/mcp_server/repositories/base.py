"""Base repository with common session helpers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.mcp_server.repositories.models import Base


class BaseRepository:
    """Thin base; holds a session and provides a generic get-by-id helper."""

    model: type[Base]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, entity_id: str):
        return self.session.get(self.model, entity_id)