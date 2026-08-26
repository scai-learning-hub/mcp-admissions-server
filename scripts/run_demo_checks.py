"""Run demo checks — smoke tests against a running MCP service.

Usage:
  python scripts/run_demo_checks.py

Checks:
  - health of the MCP service
  - capability discovery (tools/resources/prompts listed)
  - a read tool call (catalog_search_courses) with a learner token
  - an unauthorized call (leads_list_assigned with a learner token) is denied
  - a counsellor token can list assigned leads (empty is OK)
"""

from __future__ import annotations

import asyncio
import sys

import httpx

from services.counsellor_client.mcp_client import CounsellorMCPClient
from services.learner_host.mcp_client import LearnerMCPClient
from packages.shared.config import settings
from packages.shared.tokens import Role, issue_token


def _learner_token() -> str:
    return issue_token(subject="demo-learner", role=Role.LEARNER, client_id="demo-checks",
                       scopes=["catalog:read"])


def _counsellor_token() -> str:
    return issue_token(subject="demo-counsellor", role=Role.COUNSELLOR, client_id="demo-checks",
                       scopes=["lead:read:assigned"])


async def main() -> int:
    base = settings.mcp_server_url.replace("/mcp", "")
    fails: list[str] = []

    # 1. Health
    async with httpx.AsyncClient(timeout=10) as http:
        try:
            r = await http.get(base + "/health")
            ok = r.status_code == 200
        except Exception:
            ok = False
    print(f"[{'PASS' if ok else 'FAIL'}] MCP service health")
    if not ok:
        fails.append("health")

    # 2. Capability discovery + read tool (learner)
    lc = LearnerMCPClient(token=_learner_token())
    try:
        tools = await lc.list_tools()
        print(f"[{'PASS' if tools else 'FAIL'}] Capability discovery ({len(tools)} tools)")
        if not tools:
            fails.append("discovery")

        res = await lc.call_tool("catalog_search_courses", {"query": "agentic"})
        ok_read = bool(res.get("ok"))
        print(f"[{'PASS' if ok_read else 'FAIL'}] Read tool catalog_search_courses")
        if not ok_read:
            fails.append("read")
    finally:
        await lc.close()

    # 3. Unauthorized: learner calling leads_list_assigned must be denied
    lc2 = LearnerMCPClient(token=_learner_token())
    try:
        res = await lc2.call_tool("leads_list_assigned", {"limit": 5})
        denied = (not res.get("ok")) and res.get("error", {}).get("code") == "FORBIDDEN"
        print(f"[{'PASS' if denied else 'FAIL'}] Learner denied leads_list_assigned")
        if not denied:
            fails.append("authz")
    finally:
        await lc2.close()

    # 4. Counsellor client reuse
    cc = CounsellorMCPClient(token=_counsellor_token())
    try:
        res = await cc.call_tool("leads_list_assigned", {"limit": 5})
        ok_cb = bool(res.get("ok"))
        print(f"[{'PASS' if ok_cb else 'FAIL'}] Counsellor client reuses MCP (leads_list_assigned)")
        if not ok_cb:
            fails.append("reuse")
    finally:
        await cc.close()

    if fails:
        print("\nDemo checks FAILED:", ", ".join(fails))
        return 1
    print("\nAll demo checks PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
