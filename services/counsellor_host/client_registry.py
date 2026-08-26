"""Client registry for counsellor host — same pattern as learner host."""

from __future__ import annotations

from services.counsellor_host.mcp_client import CounsellorMCPClient

_clients: dict[str, CounsellorMCPClient] = {}


def register_client(thread_id: str, client: CounsellorMCPClient) -> None:
    _clients[thread_id] = client


def get_client(thread_id: str) -> CounsellorMCPClient | None:
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