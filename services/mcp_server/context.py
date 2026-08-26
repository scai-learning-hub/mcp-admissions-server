"""Per-request MCP context: principal, trace_id, request_id, audit helper.

MCP operations are kept stateless (plan §6 protocol note). Cross-call business
state is represented by server-minted values: quote_id, approval_id, lead_id.
This context object lives only for the duration of one tool call.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from uuid import uuid4

from packages.observability.tracing import span
from services.mcp_server.auth import Principal
from services.mcp_server.repositories.audit import AuditRepository
from services.mcp_server.repositories.db import session_scope
from services.mcp_server.repositories.models import ToolAuditEvent


@dataclass
class RequestContext:
    principal: Principal
    trace_id: str = field(default_factory=lambda: uuid4().hex)
    request_id: str = field(default_factory=lambda: "req_" + uuid4().hex[:16])
    source_version: str = "0.1.0"

    def audit(self, tool_name: str, args_hash: str, result_code: str, latency_ms: int) -> None:
        """Append an audit event. Failures here must not break the tool result."""
        try:
            with session_scope() as sess:
                AuditRepository(sess).append(
                    ToolAuditEvent(
                        trace_id=self.trace_id,
                        client_id=self.principal.client_id,
                        actor_id=self.principal.actor_id,
                        role=self.principal.role.value,
                        tool_name=tool_name,
                        args_hash=args_hash,
                        result_code=result_code,
                        latency_ms=latency_ms,
                    )
                )
        except Exception:
            # Audit is best-effort for tool return, but we never swallow in
            # production-grade code. For the demo we log via structlog.
            from packages.observability.logging import get_logger

            get_logger("scai.audit").warning("audit_append_failed", tool=tool_name)


def hash_args(args: dict) -> str:
    import hashlib
    import json

    canonical = json.dumps(args, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def timed(tool_name: str):
    """Decorator helper to time a tool and audit the result. Used by tools."""

    def decorator(fn):
        async def wrapper(ctx: RequestContext, *a, **kw):
            start = time.perf_counter()
            result_code = "OK"
            try:
                with span(tool_name, actor=ctx.principal.actor_id, trace=ctx.trace_id):
                    return await fn(ctx, *a, **kw)
            except Exception:
                result_code = "INTERNAL_ERROR"
                raise
            finally:
                latency = int((time.perf_counter() - start) * 1000)
                ctx.audit(tool_name, hash_args(kw or {}), result_code, latency)

        return wrapper

    return decorator


__all__ = ["RequestContext", "hash_args", "timed"]