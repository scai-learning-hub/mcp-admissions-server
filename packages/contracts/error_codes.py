"""Stable error codes and the tool result envelope.

Every tool returns one of two shapes (see plan §13):

    {"ok": True,  "data": {...}, "meta": {"request_id": "...", "source_version": "..."}}
    {"ok": False, "error": {"code": "...", "message": "...", "retryable": bool,
                            "field_errors": [...]}, "meta": {"request_id": "..."}}

The LLM sees safe, bounded messages. Detailed stack traces stay in local logs.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorCode(StrEnum):
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    COURSE_NOT_FOUND = "COURSE_NOT_FOUND"
    BATCH_NOT_AVAILABLE = "BATCH_NOT_AVAILABLE"
    QUOTE_EXPIRED = "QUOTE_EXPIRED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVAL_EXPIRED = "APPROVAL_EXPIRED"
    PAYLOAD_CHANGED = "PAYLOAD_CHANGED"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class FieldError(BaseModel):
    field: str
    message: str


class ToolError(BaseModel):
    code: ErrorCode
    message: str = Field(description="Safe, LLM-friendly message.")
    retryable: bool = False
    field_errors: list[FieldError] = Field(default_factory=list)


class ResultMeta(BaseModel):
    request_id: str
    source_version: str | None = None


class ToolSuccess(BaseModel, Generic[T]):
    ok: bool = True
    data: T
    meta: ResultMeta


class ToolFailure(BaseModel):
    ok: bool = False
    error: ToolError
    meta: ResultMeta


# A ToolResult is the discriminated union returned by every tool.
ToolResult = ToolSuccess[T] | ToolFailure


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def success(data: Any, *, request_id: str, source_version: str | None = None) -> dict[str, Any]:
    """Build a success envelope dict (kept as dict for easy JSON serialization)."""
    return {
        "ok": True,
        "data": data,
        "meta": {"request_id": request_id, "source_version": source_version},
    }


def failure(
    code: ErrorCode,
    message: str,
    *,
    request_id: str,
    retryable: bool = False,
    field_errors: list[FieldError] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": code.value,
            "message": message,
            "retryable": retryable,
            "field_errors": [fe.model_dump() for fe in (field_errors or [])],
        },
        "meta": {"request_id": request_id},
    }


__all__ = [
    "ErrorCode",
    "FieldError",
    "ResultMeta",
    "ToolError",
    "ToolFailure",
    "ToolResult",
    "ToolSuccess",
    "failure",
    "success",
]