"""Policy domain service — read current versioned policy."""

from __future__ import annotations

from sqlalchemy.orm import Session

from packages.contracts.domain import PolicyContent
from services.mcp_server.repositories.policies import PolicyRepository


class PolicyService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.policies = PolicyRepository(session)

    def get_current(self, slug: str) -> PolicyContent | None:
        row = self.policies.get_current(slug)
        if row is None:
            return None
        return PolicyContent(
            slug=row.slug,
            version=row.version,
            title=row.title,
            content_md=row.content_md,
            effective_at=row.effective_at,
            retired_at=row.retired_at,
        )


__all__ = ["PolicyService"]