"""MCP client for the counsellor console.

Shares the same transport approach as the learner host's client. Both call the
same `/mcp` endpoint — this is the reuse the demo proves. This file intentionally
duplicates a minimal client rather than importing the learner host's module,
so the two clients remain truly independent processes.
"""

from __future__ import annotations

from typing import Any

import httpx

from packages.observability.logging import get_logger
from packages.shared.config import settings

log = get_logger("scai.counsellor.mcp_client")


class CounsellorMCPClient:
    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = base_url or settings.mcp_server_url
        self.token = token or ""
        self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return
        await self._rpc("initialize", {
            "protocolVersion": settings.mcp_protocol_version,
            "capabilities": {},
            "clientInfo": {"name": "counsellor-client", "version": "0.1.0"},
        })
        self._initialized = True
        log.info("mcp_initialized", url=self.base_url)

    async def close(self) -> None:
        await self._client.aclose()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        await self.initialize()
        # Auth is via HTTP Authorization header, not a tool argument
        result = await self._rpc("tools/call", {"name": name, "arguments": arguments})
        return self._unwrap(result)

    async def list_tools(self) -> list[dict[str, Any]]:
        await self.initialize()
        result = await self._rpc("tools/list", {})
        return result.get("tools", [])

    async def get_prompt(self, name: str, arguments: dict[str, str]) -> str:
        await self.initialize()
        result = await self._rpc("prompts/get", {"name": name, "arguments": arguments})
        msgs = result.get("messages", [])
        if not msgs:
            return ""
        return msgs[0].get("content", {}).get("text", "")

    async def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        import json

        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        headers = {"Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        resp = await self._client.post(self.base_url, json=payload, headers=headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"MCP HTTP {resp.status_code}")
        body = resp.text
        if body.startswith("event:") or "data:" in body:
            for line in body.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    try:
                        data = json.loads(line[5:].strip())
                        return data.get("result", data)
                    except json.JSONDecodeError:
                        continue
            return {}
        data = resp.json()
        if "error" in data:
            raise RuntimeError(data["error"].get("message", ""))
        return data.get("result", {})

    @staticmethod
    def _unwrap(result: dict[str, Any]) -> dict[str, Any]:
        import json

        contents = result.get("content", [])
        if not contents:
            return {"ok": False, "error": {"code": "INTERNAL_ERROR", "message": "Empty"}}
        try:
            return json.loads(contents[0].get("text", "{}"))
        except json.JSONDecodeError:
            return {"ok": False, "error": {"code": "INTERNAL_ERROR", "message": "Non-JSON"}}


__all__ = ["CounsellorMCPClient"]
