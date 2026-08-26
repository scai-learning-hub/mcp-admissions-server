"""Counsellor client CLI — an independent MCP consumer.

Usage:
  python -m services.counsellor_client.cli list-tools
  python -m services.counsellor_client.cli list-leads --today
  python -m services.counsellor_client.cli lead-summary --lead-id <id>
  python -m services.counsellor_client.cli update-stage --lead-id <id> --version 1 --stage contacted
  python -m services.counsellor_client.cli prepare-callback --lead-ref <ref>

This client does NOT import the MCP server's repositories or domain services.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date

from packages.shared.tokens import Role, issue_token
from services.counsellor_client.mcp_client import CounsellorMCPClient
from services.counsellor_client.render import render_leads, render_summary, render_tools


def _counsellor_token(actor_id: str) -> str:
    return issue_token(
        subject=actor_id,
        role=Role.COUNSELLOR,
        client_id="counsellor-cli",
        scopes=["lead:read:assigned", "lead:update:assigned"],
    )


async def cmd_list_tools(client: CounsellorMCPClient) -> None:
    tools = await client.list_tools()
    print(render_tools(tools))


async def cmd_list_leads(client: CounsellorMCPClient, args: argparse.Namespace) -> None:
    today = date.today()
    params = {"limit": 50}
    if args.today:
        params["date_from"] = today.isoformat()
    res = await client.call_tool("leads_list_assigned", params)
    if res.get("ok"):
        print(render_leads(res["data"].get("leads", [])))
    else:
        print("Error:", res.get("error", {}))


async def cmd_lead_summary(client: CounsellorMCPClient, args: argparse.Namespace) -> None:
    res = await client.call_tool("leads_get_summary", {"lead_id": args.lead_id})
    if res.get("ok"):
        print(render_summary(res["data"]))
    else:
        print("Error:", res.get("error", {}))


async def cmd_update_stage(client: CounsellorMCPClient, args: argparse.Namespace) -> None:
    res = await client.call_tool("leads_update_stage", {
        "lead_id": args.lead_id,
        "expected_version": args.version,
        "new_stage": args.stage,
        "note": args.note or "CLI update",
        "idempotency_key": f"cli-{args.lead_id}-{args.version}-{args.stage}",
    })
    if res.get("ok"):
        print("Updated:", res["data"])
    else:
        print("Error:", res.get("error", {}))


async def cmd_prepare_callback(client: CounsellorMCPClient, args: argparse.Namespace) -> None:
    # Use the prompt template to build a pre-call brief
    brief = await client.get_prompt("counsellor_prepare_callback", {"lead_reference": args.lead_ref})
    print(brief)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Counsellor CLI (MCP client)")
    parser.add_argument("--actor", default="counsellor-1", help="Counsellor actor id")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-tools", help="List MCP tools")

    p_leads = sub.add_parser("list-leads", help="List assigned leads")
    p_leads.add_argument("--today", action="store_true")

    p_sum = sub.add_parser("lead-summary", help="Get a lead summary")
    p_sum.add_argument("--lead-id", required=True)

    p_upd = sub.add_parser("update-stage", help="Update a lead stage")
    p_upd.add_argument("--lead-id", required=True)
    p_upd.add_argument("--version", type=int, required=True)
    p_upd.add_argument("--stage", required=True)
    p_upd.add_argument("--note", default=None)

    p_cb = sub.add_parser("prepare-callback", help="Prepare a pre-call brief")
    p_cb.add_argument("--lead-ref", required=True)

    args = parser.parse_args()
    client = CounsellorMCPClient(token=_counsellor_token(args.actor))
    try:
        if args.cmd == "list-tools":
            await cmd_list_tools(client)
        elif args.cmd == "list-leads":
            await cmd_list_leads(client, args)
        elif args.cmd == "lead-summary":
            await cmd_lead_summary(client, args)
        elif args.cmd == "update-stage":
            await cmd_update_stage(client, args)
        elif args.cmd == "prepare-callback":
            await cmd_prepare_callback(client, args)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())