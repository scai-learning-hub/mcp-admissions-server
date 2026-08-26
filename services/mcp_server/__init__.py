"""Admissions MCP service.

This package implements the governed MCP server. It does NOT reason or own a
chat loop — it exposes stable, typed, permission-checked capabilities.
"""

from services.mcp_server.app import asgi_app, mcp

__all__ = ["asgi_app", "mcp"]