"""Client registry — stores MCP clients keyed by thread_id.

LangGraph state doesn't preserve arbitrary non-serializable objects like HTTP
clients across nodes. So we store them here and nodes look them up by thread_id.
"""

from __future__ import annotations

from services.learner_host.mcp_client import LearnerMCPClient

_clients: dict[str, LearnerMCPClient] = {}


def register_client(thread_id: str, client: LearnerMCPClient) -> None:
    _clients[thread_id] = client


def get_client(thread_id: str) -> LearnerMCPClient | None:
    return _clients.get(thread_id)


def close_all() -> None:
    for c in _clients.values():
        try:
            import asyncio

            asyncio.get_event_loop().run_until_complete(c.close())
        except Exception:
            pass
    _clients.clear()


__all__ = ["close_all", "get_client", "register_client"]