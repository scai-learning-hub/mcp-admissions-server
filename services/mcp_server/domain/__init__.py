"""Domain services — deterministic business logic.

Domain services own: fees, capacity, lead deduplication, callback rules.
They do NOT own: protocol formatting, chat reasoning, or UI state.

These services are tested without any LLM or MCP (M1 exit condition).
"""

from services.mcp_server.domain.catalog import CatalogService
from services.mcp_server.domain.fees import FeeService
from services.mcp_server.domain.leads import LeadService
from services.mcp_server.domain.policies import PolicyService

__all__ = ["CatalogService", "FeeService", "LeadService", "PolicyService"]