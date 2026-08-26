"""Render helpers for the counsellor CLI — plain text tables, no PII leakage."""

from __future__ import annotations

from typing import Any


def render_leads(leads: list[dict[str, Any]]) -> str:
    if not leads:
        return "No assigned leads found."
    lines = ["PUBLIC REF      STAGE      COURSE_ID                              CREATED"]
    for l in leads:
        lines.append(
            f"{l.get('public_reference',''):<15} {l.get('stage',''):<10} "
            f"{l.get('course_id',''):<38} {l.get('created_at','')}"
        )
    return "\n".join(lines)


def render_summary(summary: dict[str, Any]) -> str:
    lead = summary.get("lead", summary)
    parts = [
        f"Lead: {lead.get('public_reference','')} (stage: {lead.get('stage','')})",
        f"Course: {lead.get('course_id','')}",
        f"Created: {lead.get('created_at','')}",
    ]
    for cb in lead.get("callbacks", []):
        parts.append(f"  Callback: {cb.get('callback_id','')} status={cb.get('status','')} "
                     f"window={cb.get('window',{}).get('start_at','')}")
    return "\n".join(parts)


def render_tools(tools: list[dict[str, Any]]) -> str:
    lines = ["Discovered MCP tools:"]
    for t in tools:
        lines.append(f"  - {t.get('name','')}: {t.get('description','')[:80]}")
    return "\n".join(lines)


__all__ = ["render_leads", "render_summary", "render_tools"]