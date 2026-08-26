"""Typed MCP tool output models — one per tool in the capability catalogue (plan §7.1)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from packages.contracts.domain import (
    BatchSummary,
    CallbackSummary,
    CourseDetail,
    CourseSummary,
    FeeQuote,
    LeadDetail,
    LeadPreview,
    LeadSummary,
    PolicyContent,
)


class CatalogSearchCoursesOutput(BaseModel):
    courses: list[CourseSummary]
    total: int


class CatalogGetCourseOutput(BaseModel):
    course: CourseDetail


class BatchesFindUpcomingOutput(BaseModel):
    batches: list[BatchSummary]


class FeesCreateQuoteOutput(BaseModel):
    quote: FeeQuote


class PoliciesGetCurrentOutput(BaseModel):
    policy: PolicyContent


class LeadsPrepareOutput(BaseModel):
    approval_id: str
    preview: LeadPreview
    expires_at: datetime


class LeadsConfirmCreateOutput(BaseModel):
    lead_id: str
    public_reference: str
    assigned_queue: str
    stage: str


class CallbacksScheduleOutput(BaseModel):
    callback: CallbackSummary


class LeadsListAssignedOutput(BaseModel):
    leads: list[LeadSummary]
    next_cursor: str | None = None


class LeadsGetSummaryOutput(BaseModel):
    lead: LeadDetail


class LeadsUpdateStageOutput(BaseModel):
    lead_id: str
    stage: str
    row_version: int


__all__ = [
    "BatchesFindUpcomingOutput",
    "CallbacksScheduleOutput",
    "CatalogGetCourseOutput",
    "CatalogSearchCoursesOutput",
    "FeesCreateQuoteOutput",
    "LeadsConfirmCreateOutput",
    "LeadsGetSummaryOutput",
    "LeadsListAssignedOutput",
    "LeadsPrepareOutput",
    "LeadsUpdateStageOutput",
    "PoliciesGetCurrentOutput",
]