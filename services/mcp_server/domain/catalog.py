"""Catalog domain service — courses + batches (read-only business logic)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from packages.contracts.domain import (
    BatchMode,
    BatchStatus,
    BatchSummary,
    CourseDetail,
    CourseLevel,
    CourseStatus,
    CourseSummary,
    SeatInfo,
    SeatStatus,
)
from packages.contracts.error_codes import ErrorCode
from services.mcp_server.repositories.batches import BatchRepository
from services.mcp_server.repositories.courses import CourseRepository


class CatalogService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.courses = CourseRepository(session)
        self.batches = BatchRepository(session)

    # -- courses ----------------------------------------------------------

    def search_courses(
        self,
        query: str,
        *,
        mode: BatchMode | None = None,
        level: str | None = None,
        limit: int = 10,
    ) -> list[CourseSummary]:
        rows = self.courses.search(
            query, mode=mode.value if mode else None, level=level, limit=limit
        )
        return [self._course_summary(r) for r in rows]

    def get_course(self, slug_or_id: str) -> CourseDetail | None:
        row = self.courses.get_by_slug_or_id(slug_or_id)
        if row is None:
            return None
        return CourseDetail(
            id=row.id,
            slug=row.slug,
            title=row.title,
            level=CourseLevel(row.level),
            duration_weeks=row.duration_weeks,
            modes=[BatchMode(m) for m in row.modes],
            status=CourseStatus(row.status),
            description=row.description,
            topics=list(row.topics),
        )

    # -- batches ----------------------------------------------------------

    def find_upcoming_batches(
        self,
        course_id: str,
        *,
        mode: BatchMode | None = None,
        timezone_str: str = "UTC",
        limit: int = 5,
        now: datetime | None = None,
    ) -> list[BatchSummary]:
        rows = self.batches.find_upcoming(
            course_id, mode=mode.value if mode else None, now=now, limit=limit
        )
        return [self._batch_summary(r) for r in rows]

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _course_summary(row) -> CourseSummary:
        return CourseSummary(
            id=row.id,
            slug=row.slug,
            title=row.title,
            level=CourseLevel(row.level),
            duration_weeks=row.duration_weeks,
            modes=[BatchMode(m) for m in row.modes],
            status=CourseStatus(row.status),
        )

    @staticmethod
    def _batch_summary(row) -> BatchSummary:
        available = max(0, row.seats_total - row.seats_reserved)
        if available == 0:
            status = SeatStatus.FULL
        elif available <= 5:
            status = SeatStatus.LIMITED
        else:
            status = SeatStatus.AVAILABLE
        return BatchSummary(
            id=row.id,
            course_id=row.course_id,
            start_at=row.start_at,
            timezone=row.timezone,
            mode=BatchMode(row.mode),
            seats=SeatInfo(
                seats_total=row.seats_total,
                seats_reserved=row.seats_reserved,
                seats_available=available,
                status=status,
            ),
            status=BatchStatus(row.status),
        )


# Re-export for convenience
__all__ = ["CatalogService", "ErrorCode"]