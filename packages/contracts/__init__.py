"""Admissions shared contracts.

This package is the M0 contract freeze: Pydantic models for the domain and for
MCP tool inputs/outputs, plus stable error codes. It is intentionally free of
any MCP, DB, or agent-host concerns so it can be reused by the server, the
clients, and the tests without coupling.
"""

from packages.contracts.domain import (
    BatchMode,
    BatchStatus,
    CallbackStatus,
    CallbackWindow,
    CourseLevel,
    CourseSummary,
    CourseStatus,
    LeadStage,
    LeadSummary,
    PolicySummary,
    QuoteLineItem,
    SeatStatus,
)
from packages.contracts.error_codes import ErrorCode, ToolError, ToolResult
from packages.contracts.tool_inputs import (
    BatchesFindUpcomingInput,
    CallbacksScheduleInput,
    CatalogGetCourseInput,
    CatalogSearchCoursesInput,
    FeesCreateQuoteInput,
    LeadsConfirmCreateInput,
    LeadsGetSummaryInput,
    LeadsListAssignedInput,
    LeadsPrepareInput,
    LeadsUpdateStageInput,
    PoliciesGetCurrentInput,
)
from packages.contracts.tool_outputs import (
    BatchesFindUpcomingOutput,
    CallbacksScheduleOutput,
    CatalogGetCourseOutput,
    CatalogSearchCoursesOutput,
    FeesCreateQuoteOutput,
    LeadPreview,
    LeadsConfirmCreateOutput,
    LeadsGetSummaryOutput,
    LeadsListAssignedOutput,
    LeadsPrepareOutput,
    LeadsUpdateStageOutput,
    PoliciesGetCurrentOutput,
)

__all__ = [
    # domain
    "BatchMode",
    "BatchStatus",
    "CallbackStatus",
    "CallbackWindow",
    "CourseLevel",
    "CourseSummary",
    "CourseStatus",
    "LeadStage",
    "LeadSummary",
    "PolicySummary",
    "QuoteLineItem",
    "SeatStatus",
    # errors / envelope
    "ErrorCode",
    "ToolError",
    "ToolResult",
    # inputs
    "BatchesFindUpcomingInput",
    "CallbacksScheduleInput",
    "CatalogGetCourseInput",
    "CatalogSearchCoursesInput",
    "FeesCreateQuoteInput",
    "LeadsConfirmCreateInput",
    "LeadsGetSummaryInput",
    "LeadsListAssignedInput",
    "LeadsPrepareInput",
    "LeadsUpdateStageInput",
    "PoliciesGetCurrentInput",
    # outputs
    "BatchesFindUpcomingOutput",
    "CallbacksScheduleOutput",
    "CatalogGetCourseOutput",
    "CatalogSearchCoursesOutput",
    "FeesCreateQuoteOutput",
    "LeadPreview",
    "LeadsConfirmCreateOutput",
    "LeadsGetSummaryOutput",
    "LeadsListAssignedOutput",
    "LeadsPrepareOutput",
    "LeadsUpdateStageOutput",
    "PoliciesGetCurrentOutput",
]