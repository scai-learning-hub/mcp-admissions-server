"""Domain value objects and enums shared across server and clients.

These are pure Pydantic v2 models with no DB or MCP coupling. They form the
canonical wire contracts referenced by the tool input/output models.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CourseLevel(StrEnum):
    FOUNDATIONAL = "foundational"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class CourseStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    RETIRED = "retired"


class BatchMode(StrEnum):
    ONLINE = "online"
    IN_PERSON = "in_person"
    HYBRID = "hybrid"


class BatchStatus(StrEnum):
    SCHEDULED = "scheduled"
    ENROLLING = "enrolling"
    FULL = "full"
    STARTED = "started"
    CANCELLED = "cancelled"


class SeatStatus(StrEnum):
    AVAILABLE = "available"
    LIMITED = "limited"
    FULL = "full"


class LeadStage(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    ENROLLED = "enrolled"
    DROPPED = "dropped"


class CallbackStatus(StrEnum):
    REQUESTED = "requested"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class IdempotencyMixin(BaseModel):
    """Every write tool input carries an idempotency key."""

    idempotency_key: str = Field(
        min_length=4,
        max_length=128,
        description="Client-generated key; repeated writes with the same key "
        "return the original result instead of creating a duplicate.",
    )


# ---------------------------------------------------------------------------
# Read models
# ---------------------------------------------------------------------------


class CourseSummary(BaseModel):
    id: str
    slug: str
    title: str
    level: CourseLevel
    duration_weeks: int
    modes: list[BatchMode]
    status: CourseStatus


class CourseDetail(CourseSummary):
    description: str
    topics: list[str] = Field(default_factory=list)


class SeatInfo(BaseModel):
    seats_total: int
    seats_reserved: int
    seats_available: int
    status: SeatStatus


class BatchSummary(BaseModel):
    id: str
    course_id: str
    start_at: datetime
    timezone: str
    mode: BatchMode
    seats: SeatInfo
    status: BatchStatus


class QuoteLineItem(BaseModel):
    label: str
    amount: Decimal
    note: str | None = None


class FeeQuote(BaseModel):
    quote_id: str
    course_id: str
    batch_id: str
    currency: str
    line_items: list[QuoteLineItem]
    total: Decimal
    valid_until: datetime
    policy_version: str
    source_version: str


class PolicySummary(BaseModel):
    slug: str
    version: str
    title: str
    effective_at: datetime
    retired_at: datetime | None = None


class PolicyContent(PolicySummary):
    content_md: str


class CallbackWindow(BaseModel):
    start_at: datetime
    end_at: datetime
    timezone: str


class LeadSummary(BaseModel):
    """Restricted, PII-safe lead summary exposed to counsellors/learners."""

    lead_id: str
    public_reference: str
    course_id: str
    batch_id: str | None = None
    stage: LeadStage
    assigned_to: str | None = None
    created_at: datetime


class LeadDetail(LeadSummary):
    """Lead detail with explicitly permitted, redacted contact summary.

    Contact fields are intentionally NOT included here. Counsellors receive a
    bounded summary; raw PII never travels through MCP tool outputs in V1.
    """

    consent_at: datetime
    last_stage_note: str | None = None
    callbacks: list[CallbackSummary] = Field(default_factory=list)


class CallbackSummary(BaseModel):
    callback_id: str
    lead_id: str
    window: CallbackWindow
    status: CallbackStatus
    assigned_to: str | None = None


# ---------------------------------------------------------------------------
# Approval / preview (governed write surface)
# ---------------------------------------------------------------------------


class LeadPreview(BaseModel):
    """Exact payload shown to the user before confirmation."""

    contact_summary: dict[str, str] = Field(
        description="Redacted, key-only summary of contact details, e.g. "
        "{'phone': '...8910', 'email': 'a***@example.com'}. Never full PII."
    )
    course_id: str
    course_title: str
    batch_id: str
    batch_start: datetime
    mode: BatchMode
    requested_callback: CallbackWindow | None = None
    consent_at: datetime
    policy_version: str


__all__ = [
    "BatchMode",
    "BatchStatus",
    "BatchSummary",
    "CallbackStatus",
    "CallbackSummary",
    "CallbackWindow",
    "CourseDetail",
    "CourseLevel",
    "CourseStatus",
    "CourseSummary",
    "FeeQuote",
    "IdempotencyMixin",
    "LeadDetail",
    "LeadPreview",
    "LeadStage",
    "LeadSummary",
    "PolicyContent",
    "PolicySummary",
    "QuoteLineItem",
    "SeatInfo",
    "SeatStatus",
]