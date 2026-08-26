"""MCP server application — FastMCP + ASGI shell.

The MCP service does NOT reason, decide which business action to take, or own a
chat loop. It exposes stable, typed, permission-checked capabilities.

Transport: Streamable HTTP at /mcp (stateless per plan §6 protocol note).
A smoke-test stdio entrypoint is provided for the MCP inspector.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer as FastMCP
from mcp.server.mcpserver.server import Context

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
from packages.observability.logging import configure_logging, get_logger
from services.mcp_server.auth import AuthError, Principal, Role, verify_token
from services.mcp_server.config import settings
from services.mcp_server.context import RequestContext
from services.mcp_server.tools import (
    batches_find_upcoming as _batches_find_upcoming,
    callbacks_schedule as _callbacks_schedule,
    catalog_get_course as _catalog_get_course,
    catalog_search_courses as _catalog_search_courses,
    fees_create_quote as _fees_create_quote,
    leads_confirm_create as _leads_confirm_create,
    leads_get_summary as _leads_get_summary,
    leads_list_assigned as _leads_list_assigned,
    leads_prepare as _leads_prepare,
    leads_update_stage as _leads_update_stage,
    policies_get_current as _policies_get_current,
)

configure_logging(settings.log_level)
log = get_logger("scai.mcp")

mcp: FastMCP = FastMCP(
    "scai-admissions",
    # Streamable HTTP is the correct transport for independent local processes.
    # Stateless: cross-call state is server-minted (quote_id/approval_id/lead_id).
)


# ---------------------------------------------------------------------------
# Auth extraction
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Auth extraction — read Authorization header from the MCP Context
# ---------------------------------------------------------------------------


def _ctx_from_context(mcp_ctx: Context) -> RequestContext:
    """Build a RequestContext from the MCP SDK's Context object.

    Reads the Authorization header (Bearer token) from the HTTP request.
    The MCP SDK populates `context.headers` from the transport.
    """
    from packages.contracts.error_codes import ErrorCode

    headers = mcp_ctx.headers or {}
    auth_header = headers.get("authorization") or headers.get("Authorization") or ""

    token = None
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()

    if not token:
        raise AuthError(ErrorCode.UNAUTHENTICATED, "Missing or invalid credentials.")

    principal = verify_token(token)
    return RequestContext(principal=principal)


def _unauth_response() -> dict:
    from packages.contracts.error_codes import ErrorCode, failure

    return failure(ErrorCode.UNAUTHENTICATED, "Missing or invalid credentials.",
                   request_id="req_anon")


# ---------------------------------------------------------------------------
# Tool registrations — all use Context for auth, no auth_token parameter
# ---------------------------------------------------------------------------


@mcp.tool()
async def catalog_search_courses(query: str, mode: str | None = None, level: str | None = None,
                                 limit: int = 10, context: Context = None) -> dict:
    try:
        ctx = _ctx_from_context(context)
    except AuthError:
        return _unauth_response()
    args = {"query": query, "mode": mode, "level": level, "limit": limit}
    return await _catalog_search_courses(ctx, args)


@mcp.tool()
async def catalog_get_course(slug_or_id: str, context: Context = None) -> dict:
    try:
        ctx = _ctx_from_context(context)
    except AuthError:
        return _unauth_response()
    args = {"slug_or_id": slug_or_id}
    return await _catalog_get_course(ctx, args)


@mcp.tool()
async def batches_find_upcoming(course_id: str, mode: str | None = None, timezone: str = "UTC",
                                limit: int = 5, context: Context = None) -> dict:
    try:
        ctx = _ctx_from_context(context)
    except AuthError:
        return _unauth_response()
    args = {"course_id": course_id, "mode": mode, "timezone": timezone, "limit": limit}
    return await _batches_find_upcoming(ctx, args)


@mcp.tool()
async def fees_create_quote(course_id: str, batch_id: str, currency: str = "INR",
                            context: Context = None) -> dict:
    try:
        ctx = _ctx_from_context(context)
    except AuthError:
        return _unauth_response()
    args = {"course_id": course_id, "batch_id": batch_id, "currency": currency}
    return await _fees_create_quote(ctx, args)


@mcp.tool()
async def policies_get_current(slug: str, context: Context = None) -> dict:
    try:
        ctx = _ctx_from_context(context)
    except AuthError:
        return _unauth_response()
    args = {"slug": slug}
    return await _policies_get_current(ctx, args)


@mcp.tool()
async def leads_prepare(contact: dict, course_id: str, batch_id: str, consent: bool,
                        consent_at: str, requested_callback: dict | None = None,
                        context: Context = None) -> dict:
    try:
        ctx = _ctx_from_context(context)
    except AuthError:
        return _unauth_response()
    args = {
        "contact": contact, "course_id": course_id, "batch_id": batch_id, "consent": consent,
        "consent_at": consent_at, "requested_callback": requested_callback,
    }
    return await _leads_prepare(ctx, args)


@mcp.tool()
async def leads_confirm_create(approval_id: str, idempotency_key: str,
                               context: Context = None) -> dict:
    try:
        ctx = _ctx_from_context(context)
    except AuthError:
        return _unauth_response()
    args = {"approval_id": approval_id, "idempotency_key": idempotency_key}
    return await _leads_confirm_create(ctx, args)


@mcp.tool()
async def callbacks_schedule(lead_id: str, window: dict, approval_id: str,
                             idempotency_key: str, context: Context = None) -> dict:
    try:
        ctx = _ctx_from_context(context)
    except AuthError:
        return _unauth_response()
    args = {"lead_id": lead_id, "window": window, "approval_id": approval_id,
            "idempotency_key": idempotency_key}
    return await _callbacks_schedule(ctx, args)


@mcp.tool()
async def leads_list_assigned(date_from: str | None = None, date_to: str | None = None,
                              stage: str | None = None, limit: int = 20,
                              cursor: str | None = None, context: Context = None) -> dict:
    try:
        ctx = _ctx_from_context(context)
    except AuthError:
        return _unauth_response()
    args = {"date_from": date_from, "date_to": date_to, "stage": stage, "limit": limit,
            "cursor": cursor}
    return await _leads_list_assigned(ctx, args)


@mcp.tool()
async def leads_get_summary(lead_id: str, context: Context = None) -> dict:
    try:
        ctx = _ctx_from_context(context)
    except AuthError:
        return _unauth_response()
    args = {"lead_id": lead_id}
    return await _leads_get_summary(ctx, args)


@mcp.tool()
async def leads_update_stage(lead_id: str, expected_version: int, new_stage: str,
                             note: str | None = None, idempotency_key: str = "default-key",
                             context: Context = None) -> dict:
    try:
        ctx = _ctx_from_context(context)
    except AuthError:
        return _unauth_response()
    args = {"lead_id": lead_id, "expected_version": expected_version, "new_stage": new_stage,
            "note": note, "idempotency_key": idempotency_key}
    return await _leads_update_stage(ctx, args)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("scai://catalog/courses")
def resource_catalog_courses() -> str:
    import json

    from services.mcp_server.resources import catalog_courses_snapshot

    return json.dumps(catalog_courses_snapshot(), default=str)


@mcp.resource("scai://catalog/courses/{course_id}")
def resource_catalog_course(course_id: str) -> str:
    import json

    from services.mcp_server.resources import catalog_course_record

    rec = catalog_course_record(course_id)
    return json.dumps(rec or {"error": "not found"}, default=str)


@mcp.resource("scai://policies/{policy_slug}/current")
def resource_policy_current(policy_slug: str) -> str:
    import json

    from services.mcp_server.resources import policy_current

    p = policy_current(policy_slug)
    return json.dumps(p or {"error": "not found"}, default=str)


@mcp.resource("scai://schemas/lead-intake")
def resource_schema_lead_intake() -> str:
    import json

    from services.mcp_server.resources import schema_lead_intake

    return json.dumps(schema_lead_intake())


@mcp.resource("scai://schemas/fee-quote")
def resource_schema_fee_quote() -> str:
    import json

    from services.mcp_server.resources import schema_fee_quote

    return json.dumps(schema_fee_quote())


# Knowledge Base resources ---------------------------------------------------

@mcp.resource("scai://kb/articles")
def resource_kb_articles() -> str:
    """List all KB articles (title + category + tags)."""
    import json

    from services.mcp_server.resources import kb_list

    return json.dumps(kb_list())


@mcp.resource("scai://kb/articles/{article_id}")
def resource_kb_article(article_id: str) -> str:
    """Full KB article by ID."""
    import json

    from services.mcp_server.resources import kb_article

    a = kb_article(article_id)
    return json.dumps(a or {"error": "not found"}, default=str)


@mcp.resource("scai://kb/search{?q}")
def resource_kb_search(q: str = "") -> str:
    """Search KB articles by keyword."""
    import json

    from services.mcp_server.resources import kb_search

    return json.dumps(kb_search(q))


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt()
def admissions_qualify_enquiry(course_interest: str, experience: str, schedule: str) -> str:
    from services.mcp_server.prompts import admissions_qualify_enquiry as _fn

    return _fn(course_interest, experience, schedule)["template"]


@mcp.prompt()
def counsellor_prepare_callback(lead_reference: str) -> str:
    from services.mcp_server.prompts import counsellor_prepare_callback as _fn

    return _fn(lead_reference)["template"]


# ---------------------------------------------------------------------------
# ASGI app (Streamable HTTP at root) + health/audit routes
# ---------------------------------------------------------------------------

# Serve MCP at root — the SDK's streamable_http_app is a Starlette ASGI app.
# We add health/audit routes by mounting them separately on a FastAPI wrapper.
from starlette.routing import Route, Mount  # noqa: E402
from starlette.applications import Starlette  # noqa: E402
from starlette.responses import JSONResponse  # noqa: E402
import json as _json  # noqa: E402


async def _health_endpoint(request):  # noqa: ANN001
    return JSONResponse({"status": "ok", "service": "mcp-server"})


async def _kb_list_endpoint(request):  # noqa: ANN001
    """REST proxy for scai://kb/articles — for the Streamlit UI."""
    import json as _json

    from services.mcp_server.resources import kb_list

    return JSONResponse(kb_list())


async def _kb_article_endpoint(request):  # noqa: ANN001
    """REST proxy for scai://kb/articles/{id} — for the Streamlit UI."""
    from services.mcp_server.resources import kb_article

    article_id = request.path_params["article_id"]
    a = kb_article(article_id)
    if a is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(a)


async def _kb_search_endpoint(request):  # noqa: ANN001
    """REST proxy for scai://kb/search — for the Streamlit UI."""
    from services.mcp_server.resources import kb_search

    q = request.query_params.get("q", "")
    return JSONResponse(kb_search(q))


async def _audit_recent_endpoint(request):  # noqa: ANN001
    from services.mcp_server.repositories.audit import AuditRepository
    from services.mcp_server.repositories.db import session_scope

    limit = int(request.query_params.get("limit", 50))
    with session_scope() as sess:
        events = AuditRepository(sess).list_recent(limit=limit)
    return JSONResponse({
        "total": len(events),
        "events": [
            {"client_id": e.client_id, "actor_id": e.actor_id, "role": e.role,
             "tool": e.tool_name, "result": e.result_code, "latency_ms": e.latency_ms,
             "trace_id": e.trace_id[:12], "at": e.created_at.isoformat()}
            for e in events
        ],
    })


async def _audit_by_client_endpoint(request):  # noqa: ANN001
    from services.mcp_server.repositories.audit import AuditRepository
    from services.mcp_server.repositories.db import session_scope

    with session_scope() as sess:
        events = AuditRepository(sess).list_recent(limit=200)
    by_client: dict[str, dict] = {}
    for e in events:
        c = by_client.setdefault(e.client_id, {"calls": 0, "tools": set(), "actors": set()})
        c["calls"] += 1
        c["tools"].add(e.tool_name)
        c["actors"].add(e.actor_id)
    return JSONResponse({
        "clients": {
            cid: {**data, "tools": sorted(data["tools"]), "actors": sorted(data["actors"])}
            for cid, data in by_client.items()
        }
    })


_mcp_app = mcp.streamable_http_app()

# Build a Starlette app that routes /health and /audit/* to our endpoints,
# and everything else to the MCP app. We must preserve the MCP app's lifespan
# so the task group initializes (without it: "Task group is not initialized").
from contextlib import asynccontextmanager  # noqa: E402


@asynccontextmanager
async def _lifespan(app):  # noqa: ANN001
    # The MCP streamable_http_app is a Starlette app with its own lifespan
    # stored in its router. Invoke it directly.
    async with _mcp_app.router.lifespan_context(app):
        yield


_asgi = Starlette(
    routes=[
        Route("/health", _health_endpoint, methods=["GET"]),
        Route("/kb/articles", _kb_list_endpoint, methods=["GET"]),
        Route("/kb/articles/{article_id}", _kb_article_endpoint, methods=["GET"]),
        Route("/kb/search", _kb_search_endpoint, methods=["GET"]),
        Route("/audit/recent", _audit_recent_endpoint, methods=["GET"]),
        Route("/audit/by-client", _audit_by_client_endpoint, methods=["GET"]),
        Mount("/", app=_mcp_app),
    ],
    lifespan=_lifespan,
)
asgi_app = _asgi


def main_stdio() -> None:
    """Smoke-test entrypoint: stdio transport for the MCP inspector."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main_stdio()


__all__ = ["asgi_app", "mcp"]
