"""Typed MCP tool input models — one per tool in the capability catalogue (plan §7.1).

Every input is a Pydantic model. Every write carries an `idempotency_key`.
Mutable-row writes carry `expected_version` for optimistic concurrency.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field

from packages.contracts.domain import BatchMode, CallbackWindow, IdempotencyMixin


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


class CatalogSearchCoursesInput(BaseModel):
    query: str = Field(default="", max_length=200)
    mode: BatchMode | None = None
    level: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class CatalogGetCourseInput(BaseModel):
    slug_or_id: str = Field(min_length=1, max_length=120)


# ---------------------------------------------------------------------------
# Batches
# ---------------------------------------------------------------------------


class BatchesFindUpcomingInput(BaseModel):
    course_id: str
    mode: BatchMode | None = None
    timezone: str = Field(default="UTC", max_length=64)
    limit: int = Field(default=5, ge=1, le=20)


# ---------------------------------------------------------------------------
# Fees
# ---------------------------------------------------------------------------


class FeesCreateQuoteInput(BaseModel):
    course_id: str
    batch_id: str
    currency: str = Field(default="INR", min_length=3, max_length=4)


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------


class PoliciesGetCurrentInput(BaseModel):
    slug: str = Field(min_length=1, max_length=120)


# ---------------------------------------------------------------------------
# Leads — governed write surface
# ---------------------------------------------------------------------------


class ContactDetails(BaseModel):
    """Minimum contact details for lead creation. Redacted in previews."""

    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=6, max_length=20)
    email: EmailStr
    timezone: str = Field(default="UTC", max_length=64)


class LeadsPrepareInput(BaseModel):
    """Step 1 of governed lead creation: produce a preview + approval id.

    Creates a *pending approval only*. No lead row is written here.
    """

    contact: ContactDetails
    course_id: str
    batch_id: str
    consent: bool = Field(description="Must be True; otherwise rejected.")
    consent_at: datetime
    requested_callback: CallbackWindow | None = None


class LeadsConfirmCreateInput(IdempotencyMixin):
    """Step 2: confirm a previously prepared approval.

    Server verifies the approval is non-expired and that the payload hash
    matches the confirmed payload (server re-derives the hash from its own
    stored preview, so the client cannot change the payload here).
    """

    approval_id: str


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------


class CallbacksScheduleInput(IdempotencyMixin):
    lead_id: str
    window: CallbackWindow
    approval_id: str = Field(
        description="Approval id from a prior callbacks/leads preparation step."
    )


# ---------------------------------------------------------------------------
# Counsellor-only tools
# ---------------------------------------------------------------------------


class LeadsListAssignedInput(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    stage: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = None


class LeadsGetSummaryInput(BaseModel):
    lead_id: str


class LeadsUpdateStageInput(IdempotencyMixin):
    lead_id: str
    expected_version: int = Field(ge=0, description="Optimistic concurrency token.")
    new_stage: str
    note: str | None = Field(default=None, max_length=500)


__all__ = [
    "BatchesFindUpcomingInput",
    "CallbacksScheduleInput",
    "CatalogGetCourseInput",
    "CatalogSearchCoursesInput",
    "ContactDetails",
    "FeesCreateQuoteInput",
    "LeadsConfirmCreateInput",
    "LeadsGetSummaryInput",
    "LeadsListAssignedInput",
    "LeadsPrepareInput",
    "LeadsUpdateStageInput",
    "PoliciesGetCurrentInput",
]