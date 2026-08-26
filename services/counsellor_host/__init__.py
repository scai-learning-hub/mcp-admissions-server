"""Counsellor console — a FULLY SEPARATE agentic app.

It has its own:
  - state + graph + nodes + prompts  (not imported from learner_host)
  - FastAPI chat on port 8030         (different port from learner_host)
  - MCP client                        (wire-only, no server imports)

The server sees two different `client_id` values in audit logs:
  - "learner-host"     from port 8020
  - "counsellor-host"  from port 8030
"""