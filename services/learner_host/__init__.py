"""Learner-facing admissions host — LangGraph + FastAPI.

This host owns: conversation state, intent, tool selection, confirmation UX,
final response. It does NOT own course truth, lead persistence, or authorization
— those live in the MCP service.
"""