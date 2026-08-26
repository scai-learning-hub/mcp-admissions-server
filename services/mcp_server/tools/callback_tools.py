"""Callback tools — schedule."""

from __future__ import annotations

from packages.contracts.tool_inputs import CallbacksScheduleInput
from packages.contracts.tool_outputs import CallbacksScheduleOutput
from services.mcp_server.context import RequestContext
from services.mcp_server.domain.leads import LeadService
from services.mcp_server.tools._runner import run_tool


async def callbacks_schedule(ctx: RequestContext, args: dict) -> dict:
    async def handler(validated, sess):
        svc = LeadService(sess)
        result = svc.schedule_callback(
            actor_id=ctx.principal.actor_id,
            lead_id=validated.lead_id,
            window=validated.window,
            approval_id=validated.approval_id,
            idempotency_key=validated.idempotency_key,
        )
        if isinstance(result, tuple):
            return result
        return CallbacksScheduleOutput(callback=result)

    return await run_tool(ctx, "callbacks.schedule", CallbacksScheduleInput, args, handler)


__all__ = ["callbacks_schedule"]