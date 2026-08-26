"""Authentication: dev JWT verification + role/subject resolution.

The server validates identity and authorizes before repository access
(plan §10). Confirmation is not authorization: both checks are required.

NOTE: `Role` and `issue_token` are re-exported from `packages.shared.tokens`
so clients can import them WITHOUT importing the server. Token VERIFICATION
(Principal, AuthError, verify_token) stays here — only the server trusts tokens.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jwt

from packages.contracts.error_codes import ErrorCode
from packages.shared.config import settings
from packages.shared.tokens import Role, issue_token  # re-exported for server use


@dataclass(frozen=True)
class Principal:
    """The resolved identity of a caller."""

    actor_id: str
    role: Role
    client_id: str
    scopes: tuple[str, ...] = ()

    def has_role(self, *roles: Role) -> bool:
        return self.role in roles

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


class AuthError(Exception):
    code: ErrorCode = ErrorCode.UNAUTHENTICATED

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def verify_token(token: str) -> Principal:
    """Verify a dev JWT and return a Principal.

    Raises AuthError on invalid/expired tokens.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_signing_key,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except jwt.ExpiredSignatureError as e:
        raise AuthError(ErrorCode.UNAUTHENTICATED, "Token expired.") from e
    except jwt.InvalidTokenError as e:
        raise AuthError(ErrorCode.UNAUTHENTICATED, "Invalid token.") from e

    role_str = payload.get("role")
    try:
        role = Role(role_str)
    except ValueError as e:
        raise AuthError(ErrorCode.FORBIDDEN, f"Unknown role: {role_str}") from e

    scopes = tuple(payload.get("scopes", []))
    return Principal(
        actor_id=str(payload.get("sub", "unknown")),
        role=role,
        client_id=str(payload.get("client_id", "unknown")),
        scopes=scopes,
    )


__all__ = ["AuthError", "Principal", "Role", "issue_token", "verify_token"]