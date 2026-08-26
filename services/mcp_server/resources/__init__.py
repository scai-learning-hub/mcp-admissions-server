"""MCP resources — read-only context (plan §7.2).

Resources are for context that clients can read. Business actions remain tools.
"""

from __future__ import annotations

from services.mcp_server.repositories.db import session_scope
from services.mcp_server.domain.catalog import CatalogService
from services.mcp_server.domain.policies import PolicyService


def catalog_courses_snapshot() -> dict:
    """scai://catalog/courses — read-only catalogue snapshot."""
    with session_scope() as sess:
        svc = CatalogService(sess)
        courses = svc.search_courses("", limit=50)
        return {"courses": [c.model_dump(mode="json") for c in courses]}


def catalog_course_record(course_id: str) -> dict | None:
    """scai://catalog/courses/{course_id} — canonical course record."""
    with session_scope() as sess:
        svc = CatalogService(sess)
        course = svc.get_course(course_id)
        if course is None:
            return None
        return course.model_dump(mode="json")


def policy_current(slug: str) -> dict | None:
    """scai://policies/{policy_slug}/current — active policy."""
    with session_scope() as sess:
        svc = PolicyService(sess)
        p = svc.get_current(slug)
        if p is None:
            return None
        return p.model_dump(mode="json")


def schema_lead_intake() -> dict:
    """scai://schemas/lead-intake — current learner-facing intake contract."""
    from packages.contracts.tool_inputs import LeadsPrepareInput

    return LeadsPrepareInput.model_json_schema()


def schema_fee_quote() -> dict:
    """scai://schemas/fee-quote — explanation of quote fields and validity."""
    from packages.contracts.tool_outputs import FeesCreateQuoteOutput

    return FeesCreateQuoteOutput.model_json_schema()


# ---------------------------------------------------------------------------
# Knowledge Base — read-only FAQ / informational articles
# ---------------------------------------------------------------------------

_KB_CACHE: dict | None = None


def _load_kb() -> dict:
    global _KB_CACHE
    if _KB_CACHE is not None:
        return _KB_CACHE
    import json
    from pathlib import Path

    kb_path = Path(__file__).resolve().parents[3] / "data" / "demo_seed" / "knowledge_base.json"
    with open(kb_path, encoding="utf-8") as f:
        _KB_CACHE = json.load(f)
    return _KB_CACHE


def kb_list() -> dict:
    """scai://kb/articles — list all KB articles (title + category + tags, no body)."""
    kb = _load_kb()
    summaries = [
        {
            "id": a["id"],
            "title": a["title"],
            "category": a["category"],
            "tags": a.get("tags", []),
        }
        for a in kb.get("articles", [])
    ]
    return {"articles": summaries, "total": len(summaries)}


def kb_article(article_id: str) -> dict | None:
    """scai://kb/articles/{article_id} — full article body."""
    kb = _load_kb()
    for a in kb.get("articles", []):
        if a["id"] == article_id:
            return a
    return None


def kb_search(query: str) -> dict:
    """scai://kb/search?q=... — simple keyword search across titles, tags, and bodies."""
    kb = _load_kb()
    q = query.lower().strip()
    if not q:
        return {"results": [], "total": 0}
    results = []
    for a in kb.get("articles", []):
        haystack = f"{a['title']} {' '.join(a.get('tags', []))} {a['body']}".lower()
        if q in haystack:
            results.append({
                "id": a["id"],
                "title": a["title"],
                "category": a["category"],
                "tags": a.get("tags", []),
                "snippet": a["body"][:200] + ("..." if len(a["body"]) > 200 else ""),
            })
    return {"results": results, "total": len(results)}


__all__ = [
    "catalog_course_record",
    "catalog_courses_snapshot",
    "policy_current",
    "schema_fee_quote",
    "schema_lead_intake",
    "kb_list",
    "kb_article",
    "kb_search",
]