"""Structured JSON logging with PII redaction.

Never put raw phone numbers or email addresses in logs (plan §8 data rules).
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s-]{7,}\d)(?!\d)")
_REDACTED = "[REDACTED]"


def _redact(obj: Any) -> Any:
    if isinstance(obj, str):
        obj = _EMAIL_RE.sub(_REDACTED, obj)
        obj = _PHONE_RE.sub(_REDACTED, obj)
        return obj
    if isinstance(obj, dict):
        return {k: _redact(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(_redact(x) for x in obj)
    return obj


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog JSON output. Safe to call once at process start."""
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _redact_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )


def _redact_processor(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    return {k: _redact(v) for k, v in event_dict.items()}


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


__all__ = ["configure_logging", "get_logger"]