"""MCP tools — the governed capability surface.

Each tool:
- validates identity + authorization before repository access;
- uses Pydantic input/output models from packages.contracts;
- returns the standard {ok, data|error, meta} envelope;
- is audited (actor, client, args hash, result, latency).
"""

from services.mcp_server.tools.callback_tools import callbacks_schedule
from services.mcp_server.tools.catalog_tools import (
    catalog_get_course,
    catalog_search_courses,
)
from services.mcp_server.tools.batch_tools import batches_find_upcoming
from services.mcp_server.tools.fee_tools import fees_create_quote
from services.mcp_server.tools.lead_tools import (
    leads_confirm_create,
    leads_get_summary,
    leads_list_assigned,
    leads_prepare,
    leads_update_stage,
)
from services.mcp_server.tools.policy_tools import policies_get_current

__all__ = [
    "batches_find_upcoming",
    "callbacks_schedule",
    "catalog_get_course",
    "catalog_search_courses",
    "fees_create_quote",
    "leads_confirm_create",
    "leads_get_summary",
    "leads_list_assigned",
    "leads_prepare",
    "leads_update_stage",
    "policies_get_current",
]