"""Server-side config — re-exports from packages.shared.config.

The canonical config lives in packages.shared so clients don't have to import
the server. This module keeps `from services.mcp_server.config import settings`
working for all server-internal code.
"""

from __future__ import annotations

from packages.shared.config import Settings, get_settings, settings

__all__ = ["Settings", "get_settings", "settings"]