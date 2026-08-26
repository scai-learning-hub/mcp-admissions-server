"""Lead + lead-approval repositories."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.mcp_server.repositories.base import BaseRepository
from services.mcp_server.repositories.models import Callback, Lead, LeadApproval


class LeadApprovalRepository(BaseRepository):
    model = LeadApproval

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def create(self, approval: LeadApproval) -> LeadApproval:
        self.session.add(approval)
        self.session.flush()
        return approval

    def get(self, approval_id: str) -> LeadApproval | None:
        return self.get_by_id(approval_id)

    def consume(self, approval_id: str) -> LeadApproval | None:
        """Mark an approval as consumed. Caller must commit."""
        a = self.get(approval_id)
        if a is not None and a.status == "pending":
            a.status = "consumed"
            self.session.flush()
        return a


class LeadRepository(BaseRepository):
    model = Lead

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def create(self, lead: Lead) -> Lead:
        self.session.add(lead)
        self.session.flush()
        return lead

    def get_by_public_ref(self, public_reference: str) -> Lead | None:
        stmt = select(Lead).where(Lead.public_reference == public_reference)
        return self.session.scalars(stmt).first()

    def list_assigned(
        self,
        *,
        counsellor_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
        stage: str | None = None,
        limit: int = 20,
    ) -> list[Lead]:
        stmt = select(Lead).where(Lead.assigned_to == counsellor_id)
        if stage:
            stmt = stmt.where(Lead.stage == stage)
        if date_from:
            stmt = stmt.where(Lead.created_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc))
        if date_to:
            end = datetime.combine(date_to, datetime.min.time(), tzinfo=timezone.utc) + timedelta(days=1)
            stmt = stmt.where(Lead.created_at < end)
        stmt = stmt.order_by(Lead.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt))

    def update_stage(
        self,
        lead_id: str,
        expected_version: int,
        new_stage: str,
        note: str | None = None,
    ) -> Lead | None:
        """Optimistic concurrency update. Returns None on version mismatch."""
        lead = self.get_by_id(lead_id)
        if lead is None:
            return None
        if lead.row_version != expected_version:
            return None  # caller maps to VERSION_CONFLICT
        lead.stage = new_stage
        if note is not None:
            lead.last_stage_note = note
        lead.row_version = expected_version + 1
        self.session.flush()
        return lead

    def count_by_stage(self, counsellor_id: str) -> dict[str, int]:
        stmt = (
            select(Lead.stage, func.count(Lead.id))
            .where(Lead.assigned_to == counsellor_id)
            .group_by(Lead.stage)
        )
        return {stage: cnt for stage, cnt in self.session.execute(stmt).all()}

    def get_with_callbacks(self, lead_id: str) -> Lead | None:
        lead = self.get_by_id(lead_id)
        if lead is not None:
            # force-load callbacks
            _ = lead.callbacks
        return lead


__all__ = ["LeadApprovalRepository", "LeadRepository"]