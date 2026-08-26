"""Fee tools — create_quote."""

from __future__ import annotations

from packages.contracts.tool_inputs import FeesCreateQuoteInput
from packages.contracts.tool_outputs import FeesCreateQuoteOutput
from services.mcp_server.context import RequestContext
from services.mcp_server.domain.fees import FeeService
from services.mcp_server.tools._runner import run_tool


async def fees_create_quote(ctx: RequestContext, args: dict) -> dict:
    async def handler(validated, sess):
        svc = FeeService(sess)
        result = svc.create_quote(
            actor_id=ctx.principal.actor_id,
            course_id=validated.course_id,
            batch_id=validated.batch_id,
            currency=validated.currency,
        )
        if isinstance(result, tuple):
            return result  # (ErrorCode, message)
        return FeesCreateQuoteOutput(quote=result)

    return await run_tool(ctx, "fees.create_quote", FeesCreateQuoteInput, args, handler)


__all__ = ["fees_create_quote"]