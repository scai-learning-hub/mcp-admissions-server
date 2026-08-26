"""Unit: PII redaction in logs (plan §14, §8 data rules)."""

from __future__ import annotations

from packages.observability.logging import _redact


def test_redact_email():
    out = _redact({"msg": "contact testuser@example.com for details"})
    assert "testuser@example.com" not in out["msg"]
    assert "[REDACTED]" in out["msg"]


def test_redact_phone():
    out = _redact({"msg": "call +919999988910 please"})
    assert "+919999988910" not in out["msg"]
    assert "[REDACTED]" in out["msg"]


def test_redact_nested():
    out = _redact({"event": "lead", "contact": {"phone": "+919999988910", "email": "a@b.com"}})
    assert "+919999988910" not in str(out)
    assert "a@b.com" not in str(out)


def test_redact_list():
    out = _redact({"phones": ["+919999988910", "+918888877770"]})
    assert all("+91" not in p for p in out["phones"])