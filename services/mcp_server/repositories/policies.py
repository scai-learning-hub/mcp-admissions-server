"""Policy repository — current versioned policy by slug."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.mcp_server.repositories.base import BaseRepository
from services.mcp_server.repositories.models import Policy


class PolicyRepository(BaseRepository):
    model = Policy

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_current(self, slug: str) -> Policy | None:
        now = datetime.now(timezone.utc)
        stmt = select(Policy).where(
            Policy.slug == slug,
            Policy.effective_at <= now,
        )
        stmt = stmt.where(
            (Policy.retired_at.is_(None)) | (Policy.retired_at > now)
        ).order_by(Policy.effective_at.desc(), Policy.version.desc())
        return self.session.scalars(stmt).first()