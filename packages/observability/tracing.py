"""Minimal OpenTelemetry helpers — tracer + span helper.

Kept intentionally thin so the demo runs without a collector; spans are
no-ops if OTel is not configured. The boundary is what matters: host → MCP →
domain → DB all share a trace_id.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator
from uuid import uuid4

from opentelemetry import trace

_tracer = trace.get_tracer("scai-mcp-admissions")


def new_trace_id() -> str:
    return uuid4().hex


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[trace.Span]:
    with _tracer.start_as_current_span(name) as s:
        for k, v in attributes.items():
            s.set_attribute(k, str(v))
        yield s


__all__ = ["new_trace_id", "span"]