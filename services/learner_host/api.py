"""FastAPI shell for the learner host — chat endpoint + health + small UI backend.

Owns: conversation state, intent, tool selection, confirmation UX, final response.
Does NOT own: course truth, lead persistence, authorization (those are the MCP service).
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from packages.observability.logging import configure_logging, get_logger
from packages.shared.tokens import Role, issue_token
from packages.shared.config import settings
from services.learner_host.client_registry import register_client
from services.learner_host.graph import learner_graph
from services.learner_host.mcp_client import LearnerMCPClient

configure_logging(settings.log_level)
log = get_logger("scai.learner_host.api")

app = FastAPI(title="Learner Admissions Host", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    # For the demo, the API issues a learner token if none is supplied.
    actor_id: str | None = None


class ChatResponse(BaseModel):
    thread_id: str
    reply: str
    state: dict[str, Any]


class ConfirmRequest(BaseModel):
    thread_id: str
    confirm: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _learner_token(actor_id: str) -> str:
    return issue_token(
        subject=actor_id,
        role=Role.LEARNER,
        client_id="learner-host",
        scopes=["catalog:read", "fees:quote", "lead:create:self"],
    )


# A small per-thread client cache (in-memory; fine for the demo)
_clients: dict[str, LearnerMCPClient] = {}


def _get_client(thread_id: str, actor_id: str) -> LearnerMCPClient:
    if thread_id in _clients:
        return _clients[thread_id]
    client = LearnerMCPClient(token=_learner_token(actor_id))
    _clients[thread_id] = client
    return client


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "learner-host"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    import uuid

    thread_id = req.thread_id or str(uuid.uuid4())
    actor_id = req.actor_id or "learner-demo"
    client = _get_client(thread_id, actor_id)

    # Load prior conversation from LangGraph checkpoint so the chat is interactive
    config = {"configurable": {"thread_id": thread_id}}
    prior_messages: list[dict] = []
    try:
        saved = await learner_graph.aget_state(config)
        if saved and saved.values and saved.values.get("messages"):
            prior_messages = list(saved.values["messages"])
    except Exception:
        pass  # first turn — no checkpoint yet

    new_messages = prior_messages + [{"role": "user", "content": req.message}]

    initial_state = {
        "thread_id": thread_id,
        "actor_id": actor_id,
        "messages": new_messages,
        "facts": {},
        "errors": [],
    }
    register_client(thread_id, client)
    try:
        final = await learner_graph.ainvoke(initial_state, config=config)
    except Exception as e:
        log.error("graph_error", error=str(e))
        raise HTTPException(status_code=500, detail="graph_error") from e

    reply = ""
    for m in reversed(final.get("messages", [])):
        if isinstance(m, dict) and m.get("role") == "assistant":
            reply = m.get("content", "")
            break

    # Strip non-serializable fields before returning
    safe = {k: v for k, v in final.items() if k != "_client" and not callable(v)}
    return ChatResponse(thread_id=thread_id, reply=reply, state=safe)


@app.post("/confirm", response_model=ChatResponse)
async def confirm(req: ConfirmRequest) -> ChatResponse:
    """Resume the graph after an interrupt with the user's confirmation."""
    config = {"configurable": {"thread_id": req.thread_id}}
    try:
        final = await learner_graph.ainvoke(None, config=config)
    except Exception as e:
        log.error("confirm_error", error=str(e))
        raise HTTPException(status_code=500, detail="confirm_error") from e

    reply = ""
    for m in reversed(final.get("messages", [])):
        if isinstance(m, dict) and m.get("role") == "assistant":
            reply = m.get("content", "")
            break
    safe = {k: v for k, v in final.items() if k != "_client" and not callable(v)}
    return ChatResponse(thread_id=req.thread_id, reply=reply, state=safe)


@app.on_event("shutdown")
async def shutdown() -> None:
    for c in _clients.values():
        await c.close()
    _clients.clear()