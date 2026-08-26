"""Fee plan + fee quote repositories."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.mcp_server.repositories.base import BaseRepository
from services.mcp_server.repositories.models import FeePlan, FeeQuote


class FeePlanRepository(BaseRepository):
    model = FeePlan

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def current_plan(self, course_id: str, *, currency: str = "INR") -> FeePlan | None:
        now = datetime.now(timezone.utc)
        stmt = select(FeePlan).where(
            FeePlan.course_id == course_id,
            FeePlan.currency == currency,
            FeePlan.valid_from <= now,
        )
        stmt = stmt.where(
            (FeePlan.valid_to.is_(None)) | (FeePlan.valid_to > now)
        ).order_by(FeePlan.valid_from.desc())
        return self.session.scalars(stmt).first()


class FeeQuoteRepository(BaseRepository):
    model = FeeQuote

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def create(self, quote: FeeQuote) -> FeeQuote:
        self.session.add(quote)
        self.session.flush()
        return quote

    def get(self, quote_id: str) -> FeeQuote | None:
        return self.get_by_id(quote_id)