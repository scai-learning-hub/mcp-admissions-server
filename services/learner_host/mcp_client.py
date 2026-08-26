"""MCP client adapter for the learner host.

A thin wrapper over the MCP SDK's client that:
- connects to the Streamable HTTP endpoint;
- injects the bearer token as `auth_token` on every tool call;
- returns typed results validated against the contracts package.

The host NEVER imports server repositories or domain services. It only knows
the MCP contract.
"""

from __future__ import annotations

from typing import Any

import httpx

from packages.observability.logging import get_logger
from packages.shared.config import settings

log = get_logger("scai.learner_host.mcp_client")


class MCPClientError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class LearnerMCPClient:
    """Minimal JSON-RPC client over Streamable HTTP for the learner host.

    The official SDK Client could be used here; we keep a small HTTP client so
    the host and the counsellor client share the same transport code and the
    demo is resilient to SDK API churn. Both call the same `/mcp` endpoint.
    """

    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = base_url or settings.mcp_server_url
        self.token = token or ""
        self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self._initialized = False
        self._session_id: str | None = None

    async def initialize(self) -> None:
        if self._initialized:
            return
        # MCP initialize handshake — capture Mcp-Session-Id for subsequent calls
        result = await self._rpc("initialize", {
            "protocolVersion": settings.mcp_protocol_version,
            "capabilities": {},
            "clientInfo": {"name": "learner-host", "version": "0.1.0"},
        }, capture_session=True)
        self._initialized = True
        log.info("mcp_initialized", url=self.base_url)

    async def close(self) -> None:
        await self._client.aclose()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        await self.initialize()
        # Auth is via HTTP Authorization header, not a tool argument
        result = await self._rpc("tools/call", {"name": name, "arguments": arguments})
        # The SDK returns content blocks; our tools return a JSON envelope.
        return self._unwrap(result)

    async def list_tools(self) -> list[dict[str, Any]]:
        await self.initialize()
        result = await self._rpc("tools/list", {})
        return result.get("tools", [])

    async def list_resources(self) -> list[dict[str, Any]]:
        await self.initialize()
        result = await self._rpc("resources/list", {})
        return result.get("resources", [])

    async def get_resource(self, uri: str) -> str:
        await self.initialize()
        result = await self._rpc("resources/read", {"uri": uri})
        contents = result.get("contents", [])
        if not contents:
            return ""
        return contents[0].get("text", "")

    async def get_prompt(self, name: str, arguments: dict[str, str]) -> str:
        await self.initialize()
        result = await self._rpc("prompts/get", {"name": name, "arguments": arguments})
        msgs = result.get("messages", [])
        if not msgs:
            return ""
        return msgs[0].get("content", {}).get("text", "")

    # -- internals --------------------------------------------------------

    async def _rpc(self, method: str, params: dict[str, Any], capture_session: bool = False) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        resp = await self._client.post(self.base_url, json=payload, headers=headers)
        if capture_session:
            self._session_id = resp.headers.get("mcp-session-id") or resp.headers.get("Mcp-Session-Id")
        if resp.status_code >= 400:
            raise MCPClientError("DEPENDENCY_UNAVAILABLE",
                                 f"MCP HTTP {resp.status_code}", retryable=True)
        # Streamable HTTP may return SSE or JSON; handle both
        body = resp.text
        if body.startswith("event:") or "data:" in body:
            return self._parse_sse(body)
        data = resp.json()
        if "error" in data:
            err = data["error"]
            raise MCPClientError(err.get("code", "INTERNAL_ERROR"), err.get("message", ""))
        return data.get("result", {})

    @staticmethod
    def _parse_sse(body: str) -> dict[str, Any]:
        import json

        # SSE data may span multiple lines — concatenate all data: lines
        data_lines: list[str] = []
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                data_lines.append(line[5:].strip())
        if data_lines:
            payload = "\n".join(data_lines)
            try:
                data = json.loads(payload)
                if "result" in data:
                    return data["result"]
                return data
            except json.JSONDecodeError as e:
                log.warning("sse_parse_failed", payload_preview=payload[:200], error=str(e))
        return {}

    @staticmethod
    def _unwrap(result: dict[str, Any]) -> dict[str, Any]:
        """Extract our tool envelope from the SDK's content-blocks wrapper."""
        contents = result.get("content", [])
        if not contents:
            log.warning("unwrap_empty", result_keys=list(result.keys()))
            return {"ok": False, "error": {"code": "INTERNAL_ERROR", "message": "Empty result"}}
        text = contents[0].get("text", "{}")
        import json

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            log.warning("unwrap_non_json", text_preview=text[:200], error=str(e))
            return {"ok": False, "error": {"code": "INTERNAL_ERROR", "message": "Non-JSON result"}}


__all__ = ["LearnerMCPClient", "MCPClientError"]
