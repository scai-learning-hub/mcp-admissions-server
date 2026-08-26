"""Lead tools — the governed write surface + counsellor reads."""

from __future__ import annotations

from packages.contracts.tool_inputs import (
    LeadsConfirmCreateInput,
    LeadsGetSummaryInput,
    LeadsListAssignedInput,
    LeadsPrepareInput,
    LeadsUpdateStageInput,
)
from packages.contracts.tool_outputs import (
    LeadsConfirmCreateOutput,
    LeadsGetSummaryOutput,
    LeadsListAssignedOutput,
    LeadsPrepareOutput,
    LeadsUpdateStageOutput,
)
from services.mcp_server.context import RequestContext
from services.mcp_server.domain.leads import LeadService
from services.mcp_server.tools._runner import run_tool


async def leads_prepare(ctx: RequestContext, args: dict) -> dict:
    async def handler(validated, sess):
        svc = LeadService(sess)
        result = svc.prepare_with_approval(
            actor_id=ctx.principal.actor_id,
            contact=validated.contact.model_dump(),
            course_id=validated.course_id,
            batch_id=validated.batch_id,
            consent=validated.consent,
            consent_at=validated.consent_at,
            requested_callback=validated.requested_callback,
        )
        if isinstance(result, tuple):
            return result  # (ErrorCode, message)
        approval_id, preview, expires_at = result
        return LeadsPrepareOutput(approval_id=approval_id, preview=preview, expires_at=expires_at)

    return await run_tool(ctx, "leads.prepare", LeadsPrepareInput, args, handler)


async def leads_confirm_create(ctx: RequestContext, args: dict) -> dict:
    async def handler(validated, sess):
        svc = LeadService(sess)
        result = svc.confirm_create(
            actor_id=ctx.principal.actor_id,
            approval_id=validated.approval_id,
            idempotency_key=validated.idempotency_key,
        )
        if isinstance(result, tuple):
            return result
        lead_id, public_ref, queue, stage = result
        return LeadsConfirmCreateOutput(
            lead_id=lead_id,
            public_reference=public_ref,
            assigned_queue=queue,
            stage=stage,
        )

    return await run_tool(ctx, "leads.confirm_create", LeadsConfirmCreateInput, args, handler)


async def leads_list_assigned(ctx: RequestContext, args: dict) -> dict:
    async def handler(validated, sess):
        svc = LeadService(sess)
        leads = svc.list_assigned(
            counsellor_id=ctx.principal.actor_id,
            date_from=validated.date_from,
            date_to=validated.date_to,
            stage=validated.stage,
            limit=validated.limit,
        )
        return LeadsListAssignedOutput(leads=leads, next_cursor=None)

    return await run_tool(ctx, "leads.list_assigned", LeadsListAssignedInput, args, handler)


async def leads_get_summary(ctx: RequestContext, args: dict) -> dict:
    async def handler(validated, sess):
        svc = LeadService(sess)
        # Counsellors are scoped to assigned leads; learners don't reach here.
        counsellor_id = ctx.principal.actor_id if ctx.principal.role.value == "counsellor" else None
        detail = svc.get_summary(validated.lead_id, counsellor_id=counsellor_id)
        if detail is None:
            from packages.contracts.error_codes import ErrorCode

            return (ErrorCode.COURSE_NOT_FOUND, "Lead not found or not assigned to you.")
        return LeadsGetSummaryOutput(lead=detail)

    return await run_tool(ctx, "leads.get_summary", LeadsGetSummaryInput, args, handler)


async def leads_update_stage(ctx: RequestContext, args: dict) -> dict:
    async def handler(validated, sess):
        svc = LeadService(sess)
        counsellor_id = ctx.principal.actor_id if ctx.principal.role.value == "counsellor" else None
        result = svc.update_stage(
            lead_id=validated.lead_id,
            expected_version=validated.expected_version,
            new_stage=validated.new_stage,
            note=validated.note,
            actor_id=ctx.principal.actor_id,
            idempotency_key=validated.idempotency_key,
            counsellor_id=counsellor_id,
        )
        if isinstance(result, tuple):
            return result
        lead_id, stage, version = result
        return LeadsUpdateStageOutput(lead_id=lead_id, stage=stage, row_version=version)

    return await run_tool(ctx, "leads.update_stage", LeadsUpdateStageInput, args, handler)


__all__ = [
    "leads_confirm_create",
    "leads_get_summary",
    "leads_list_assigned",
    "leads_prepare",
    "leads_update_stage",
]