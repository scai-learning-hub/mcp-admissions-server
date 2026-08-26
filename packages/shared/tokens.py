"""Role enum + dev token issuance usable by all clients.

Token VERIFICATION (Principal resolution, AuthError) stays in
`services.mcp_server.auth` — only the server trusts tokens. Clients only need
to ISSUE them (for the demo) and know the role names.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import StrEnum

import jwt

from packages.shared.config import settings


class Role(StrEnum):
    LEARNER = "learner"
    COUNSELLOR = "counsellor"
    AUDITOR = "auditor"
    ADMIN = "admin"  # admin is NOT exposed via MCP tools in V1


def issue_token(
    *,
    subject: str,
    role: Role,
    client_id: str,
    scopes: list[str] | None = None,
    expires_in_seconds: int = 3600,
) -> str:
    """Issue a signed dev JWT. Used by scripts/issue_dev_token.py and clients."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role.value,
        "client_id": client_id,
        "scopes": scopes or [],
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_signing_key, algorithm="HS256")


__all__ = ["Role", "issue_token"]