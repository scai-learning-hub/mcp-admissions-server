"""Unit: lead payload normalization + redaction (plan §14)."""

from __future__ import annotations

from services.mcp_server.domain.leads import _contact_summary, _redact_email, _redact_phone


def test_redact_phone_keeps_last_four():
    assert _redact_phone("+919999988910") == "...8910"
    assert _redact_phone("123") == "****"


def test_redact_email_keeps_domain():
    redacted = _redact_email("testuser@example.com")
    assert redacted.endswith("@example.com")
    assert redacted.startswith("a***")


def test_contact_summary_redacts_pii():
    summary = _contact_summary({
        "name": "TestUser",
        "phone": "+919999988910",
        "email": "testuser@example.com",
        "timezone": "Asia/Kolkata",
    })
    assert "8910" in summary["phone"]
    assert "+919999988910" not in summary["phone"]
    assert "testuser@example.com" not in summary["email"]
    assert summary["name"] == "TestUser"  # name is not PII for the demo