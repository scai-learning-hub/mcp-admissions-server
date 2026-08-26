"""Course repository — search and fetch courses."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from services.mcp_server.repositories.base import BaseRepository
from services.mcp_server.repositories.models import Course


class CourseRepository(BaseRepository):
    model = Course

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def search(
        self,
        query: str,
        *,
        mode: str | None = None,
        level: str | None = None,
        limit: int = 10,
    ) -> list[Course]:
        stmt = select(Course).where(Course.status == "published")
        if query:
            like = f"%{query.lower()}%"
            stmt = stmt.where(
                or_(
                    Course.title.ilike(like),
                    Course.slug.ilike(like),
                    Course.description.ilike(like),
                )
            )
        if level:
            stmt = stmt.where(Course.level == level)
        if mode:
            # modes stored as JSONB array; use containment check
            stmt = stmt.where(Course.modes.contains([mode]))
        stmt = stmt.order_by(Course.title).limit(limit)
        return list(self.session.scalars(stmt))

    def get_by_slug(self, slug: str) -> Course | None:
        stmt = select(Course).where(Course.slug == slug)
        return self.session.scalars(stmt).first()

    def get_by_slug_or_id(self, slug_or_id: str) -> Course | None:
        by_slug = self.get_by_slug(slug_or_id)
        if by_slug is not None:
            return by_slug
        return self.get_by_id(slug_or_id)