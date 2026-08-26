"""SQLAlchemy 2 ORM models — plan §8 core tables.

Authoritative business state lives here. Models are intentionally close to the
data-model table in the plan. Contact values are stored encrypted (see
`contact_ciphertext`); raw PII is never stored in plaintext.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all models."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid4())


# ---------------------------------------------------------------------------
# Courses / batches / fees / policies
# ---------------------------------------------------------------------------


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    level: Mapped[str] = mapped_column(String(20), index=True)
    duration_weeks: Mapped[int] = mapped_column(Integer)
    modes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(20), default="published", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    topics: Mapped[list[str]] = mapped_column(JSONB, default=list)
    row_version: Mapped[int] = mapped_column(Integer, default=1)

    batches: Mapped[list[Batch]] = relationship(back_populates="course")
    fee_plans: Mapped[list[FeePlan]] = relationship(back_populates="course")


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    mode: Mapped[str] = mapped_column(String(20), index=True)
    seats_total: Mapped[int] = mapped_column(Integer)
    seats_reserved: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="enrolling", index=True)
    row_version: Mapped[int] = mapped_column(Integer, default=1)

    course: Mapped[Course] = relationship(back_populates="batches")
    callbacks: Mapped[list[Callback]] = relationship(back_populates="batch")

    __table_args__ = (
        CheckConstraint("seats_total >= 0", name="ck_batches_seats_total_nonneg"),
        CheckConstraint("seats_reserved >= 0", name="ck_batches_seats_reserved_nonneg"),
        CheckConstraint("seats_reserved <= seats_total", name="ck_batches_reserved_le_total"),
    )


class FeePlan(Base):
    __tablename__ = "fee_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    currency: Mapped[str] = mapped_column(String(4), default="INR")
    base_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    installment_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    policy_version: Mapped[str] = mapped_column(String(40), default="1")

    course: Mapped[Course] = relationship(back_populates="fee_plans")


class FeeQuote(Base):
    __tablename__ = "fee_quotes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    actor_id: Mapped[str] = mapped_column(String(120), index=True)
    course_id: Mapped[str] = mapped_column(String(36), index=True)
    batch_id: Mapped[str] = mapped_column(String(36), index=True)
    currency: Mapped[str] = mapped_column(String(4), default="INR")
    amount_json: Mapped[dict] = mapped_column(JSONB)
    total: Mapped[float] = mapped_column(Numeric(12, 2))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_version: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(120), index=True)
    version: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    content_md: Mapped[str] = mapped_column(Text)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("slug", "version", name="uq_policies_slug_version"),)


# ---------------------------------------------------------------------------
# Governed writes: approvals, leads, callbacks
# ---------------------------------------------------------------------------


class LeadApproval(Base):
    """Pending approval for a lead/callback write.

    Lead creation requires a non-expired approval whose payload hash matches
    the confirmed payload (plan §8).
    """

    __tablename__ = "lead_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    actor_id: Mapped[str] = mapped_column(String(120), index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), index=True)
    preview_json: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    public_reference: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    contact_ciphertext: Mapped[str] = mapped_column(Text)
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    course_id: Mapped[str] = mapped_column(String(36), index=True)
    batch_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    stage: Mapped[str] = mapped_column(String(20), default="new", index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    last_stage_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    row_version: Mapped[int] = mapped_column(Integer, default=1)

    callbacks: Mapped[list[Callback]] = relationship(back_populates="lead")

    __table_args__ = (Index("ix_leads_assigned_stage", "assigned_to", "stage"),)


class Callback(Base):
    __tablename__ = "callbacks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    lead_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("leads.id", ondelete="CASCADE"), index=True
    )
    batch_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("batches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    requested_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    requested_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    assigned_to: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="requested", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    row_version: Mapped[int] = mapped_column(Integer, default=1)

    lead: Mapped[Lead] = relationship(back_populates="callbacks")
    batch: Mapped[Batch | None] = relationship(back_populates="callbacks")


# ---------------------------------------------------------------------------
# Audit + idempotency
# ---------------------------------------------------------------------------


class ToolAuditEvent(Base):
    """Append-only execution evidence (plan §5, §8).

    Never raw PII in args_hash; we hash arguments, not the arguments themselves.
    """

    __tablename__ = "tool_audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    client_id: Mapped[str] = mapped_column(String(120), index=True)
    actor_id: Mapped[str] = mapped_column(String(120), index=True)
    role: Mapped[str] = mapped_column(String(20))
    tool_name: Mapped[str] = mapped_column(String(80), index=True)
    args_hash: Mapped[str] = mapped_column(String(64))
    result_code: Mapped[str] = mapped_column(String(40))
    latency_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    __table_args__ = (Index("ix_audit_tool_created", "tool_name", "created_at"),)


class IdempotencyRecord(Base):
    """Idempotency key store — actor+tool+key unique."""

    __tablename__ = "idempotency_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    actor_id: Mapped[str] = mapped_column(String(120), index=True)
    tool_name: Mapped[str] = mapped_column(String(80), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    result_reference: Mapped[str] = mapped_column(String(120))
    result_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        UniqueConstraint("actor_id", "tool_name", "idempotency_key", name="uq_idempotency_actor_tool_key"),
    )


__all__ = [
    "Base",
    "Batch",
    "Callback",
    "Course",
    "FeePlan",
    "FeeQuote",
    "IdempotencyRecord",
    "Lead",
    "LeadApproval",
    "Policy",
    "ToolAuditEvent",
]