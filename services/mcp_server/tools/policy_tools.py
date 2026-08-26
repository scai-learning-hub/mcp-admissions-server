"""Policy tools — get_current."""

from __future__ import annotations

from packages.contracts.tool_inputs import PoliciesGetCurrentInput
from packages.contracts.tool_outputs import PoliciesGetCurrentOutput
from services.mcp_server.context import RequestContext
from services.mcp_server.domain.policies import PolicyService
from services.mcp_server.tools._runner import run_tool


async def policies_get_current(ctx: RequestContext, args: dict) -> dict:
    async def handler(validated, sess):
        svc = PolicyService(sess)
        policy = svc.get_current(validated.slug)
        if policy is None:
            from packages.contracts.error_codes import ErrorCode

            return (ErrorCode.COURSE_NOT_FOUND, "Policy not found.")
        return PoliciesGetCurrentOutput(policy=policy)

    return await run_tool(ctx, "policies.get_current", PoliciesGetCurrentInput, args, handler)


__all__ = ["policies_get_current"]