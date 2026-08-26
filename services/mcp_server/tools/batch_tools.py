"""Batch tools — find_upcoming."""

from __future__ import annotations

from packages.contracts.tool_inputs import BatchesFindUpcomingInput
from packages.contracts.tool_outputs import BatchesFindUpcomingOutput
from services.mcp_server.context import RequestContext
from services.mcp_server.domain.catalog import CatalogService
from services.mcp_server.tools._runner import run_tool


async def batches_find_upcoming(ctx: RequestContext, args: dict) -> dict:
    async def handler(validated, sess):
        svc = CatalogService(sess)
        # Verify course exists; if not, return typed error
        if svc.courses.get_by_id(validated.course_id) is None:
            from packages.contracts.error_codes import ErrorCode

            return (ErrorCode.COURSE_NOT_FOUND, "Course not found.")
        batches = svc.find_upcoming_batches(
            validated.course_id,
            mode=validated.mode,
            timezone_str=validated.timezone,
            limit=validated.limit,
        )
        return BatchesFindUpcomingOutput(batches=batches)

    return await run_tool(ctx, "batches.find_upcoming", BatchesFindUpcomingInput, args, handler)


__all__ = ["batches_find_upcoming"]