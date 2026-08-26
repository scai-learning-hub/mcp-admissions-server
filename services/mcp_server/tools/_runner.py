"""Shared tool execution helpers.

Every tool follows the same shape:
  1. resolve principal from the request context
  2. authorize (role + scope)
  3. validate input via Pydantic
  4. call domain service inside a DB session
  5. audit (actor, client, args hash, result, latency)
  6. return the standard envelope

Keeping this in one place makes the per-tool files tiny and the contract uniform.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from packages.contracts.error_codes import ErrorCode, failure, success
from services.mcp_server.auth import AuthError, Principal, Role
from services.mcp_server.context import RequestContext
from services.mcp_server.repositories.audit import AuditRepository
from services.mcp_server.repositories.db import session_scope
from services.mcp_server.repositories.models import ToolAuditEvent

T = TypeVar("T", bound=BaseModel)

# Role -> allowed tools map (server-side enforcement; metadata is not a substitute)
ROLE_TOOLS: dict[Role, set[str]] = {
    Role.LEARNER: {
        "catalog.search_courses",
        "catalog.get_course",
        "batches.find_upcoming",
        "fees.create_quote",
        "policies.get_current",
        "leads.prepare",
        "leads.confirm_create",
        "callbacks.schedule",
    },
    Role.COUNSELLOR: {
        "catalog.search_courses",
        "catalog.get_course",
        "batches.find_upcoming",
        "fees.create_quote",
        "policies.get_current",
        "callbacks.schedule",
        "leads.list_assigned",
        "leads.get_summary",
        "leads.update_stage",
    },
    Role.AUDITOR: set(),  # auditor reads audit events via a dedicated view, not tools
}


def authorize(principal: Principal, tool_name: str) -> ErrorCode | None:
    allowed = ROLE_TOOLS.get(principal.role, set())
    if tool_name not in allowed:
        return ErrorCode.FORBIDDEN
    return None


def _hash_args(args: dict[str, Any]) -> str:
    canonical = json.dumps(args, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _audit(ctx: RequestContext, tool_name: str, args_hash: str, result_code: str, latency_ms: int) -> None:
    try:
        with session_scope() as sess:
            AuditRepository(sess).append(
                ToolAuditEvent(
                    trace_id=ctx.trace_id,
                    client_id=ctx.principal.client_id,
                    actor_id=ctx.principal.actor_id,
                    role=ctx.principal.role.value,
                    tool_name=tool_name,
                    args_hash=args_hash,
                    result_code=result_code,
                    latency_ms=latency_ms,
                )
            )
    except Exception:
        from packages.observability.logging import get_logger

        get_logger("scai.audit").warning("audit_append_failed", tool=tool_name)


async def run_tool(
    ctx: RequestContext,
    tool_name: str,
    input_model: type[T],
    raw_args: dict[str, Any],
    handler: Callable[[T, Any], Awaitable[Any]],
) -> dict[str, Any]:
    """Standard tool runner. `handler` receives (validated_input, session)."""
    start = time.perf_counter()
    args_hash = _hash_args(raw_args)
    result_code = "OK"

    try:
        # 1. authorize
        err = authorize(ctx.principal, tool_name)
        if err is not None:
            result_code = err.value
            return failure(
                err,
                "You are not authorized to call this tool.",
                request_id=ctx.request_id,
            )

        # 2. validate input
        try:
            validated = input_model.model_validate(raw_args)
        except ValidationError as e:
            result_code = ErrorCode.VALIDATION_FAILED.value
            return failure(
                ErrorCode.VALIDATION_FAILED,
                "Input validation failed.",
                request_id=ctx.request_id,
                retryable=False,
                field_errors=[
                    {"field": ".".join(str(x) for x in err["loc"]), "message": err["msg"]}
                    for err in e.errors()
                ],
            )

        # 3. run handler in a session
        from services.mcp_server.repositories.db import session_scope

        with session_scope() as sess:
            data = await handler(validated, sess)

        if isinstance(data, tuple) and len(data) == 2 and isinstance(data[0], ErrorCode):
            code, msg = data
            result_code = code.value
            return failure(code, msg, request_id=ctx.request_id, retryable=code in {
                ErrorCode.APPROVAL_EXPIRED,
                ErrorCode.QUOTE_EXPIRED,
                ErrorCode.VERSION_CONFLICT,
                ErrorCode.RATE_LIMITED,
                ErrorCode.DEPENDENCY_UNAVAILABLE,
            })

        return success(data.model_dump(mode="json") if hasattr(data, "model_dump") else data,
                       request_id=ctx.request_id, source_version=ctx.source_version)

    except AuthError as e:
        result_code = e.code.value
        return failure(e.code, e.message, request_id=ctx.request_id)
    except Exception as e:
        result_code = ErrorCode.INTERNAL_ERROR.value
        from packages.observability.logging import get_logger

        get_logger("scai.tools").error("tool_internal_error", tool=tool_name, error=str(e))
        return failure(
            ErrorCode.INTERNAL_ERROR,
            "An internal error occurred. See logs with this request_id.",
            request_id=ctx.request_id,
        )
    finally:
        latency = int((time.perf_counter() - start) * 1000)
        _audit(ctx, tool_name, args_hash, result_code, latency)


def sync_handler(fn: Callable[[T, Any], Any]) -> Callable[[T, Any], Awaitable[Any]]:
    """Wrap a synchronous handler into an async one."""

    async def wrapper(validated: T, sess: Any) -> Any:
        return fn(validated, sess)

    return wrapper


__all__ = ["ROLE_TOOLS", "authorize", "run_tool", "sync_handler"]