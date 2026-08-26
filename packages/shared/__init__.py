"""Shared configuration + token helpers usable by ALL clients and the server.

This lives in `packages/shared` (not `services/mcp_server`) so that the
counsellor client and learner host can use it WITHOUT importing the MCP
server's internals (plan §11: "The counsellor client must not import the MCP
server's repositories or domain services.").

Only config values + the Role enum + dev token issuance live here. Token
VERIFICATION (Principal resolution) stays in the server, because only the
server needs to trust tokens.
"""

from __future__ import annotations

from packages.shared.config import Settings, get_settings, settings
from packages.shared.tokens import Role, issue_token

__all__ = ["Role", "Settings", "get_settings", "issue_token", "settings"]