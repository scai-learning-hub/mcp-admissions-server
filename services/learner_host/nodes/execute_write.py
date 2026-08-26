"""Node: execute_write — resume only with a matching confirmation token."""

from __future__ import annotations

from uuid import uuid4

from services.learner_host.client_registry import get_client
from services.learner_host.state import LearnerState


async def execute_write(state: LearnerState) -> LearnerState:
    if not state.get("confirmed"):
        return {**state, "lead_reference": None, "callback_reference": None}
    client = get_client(state.get("thread_id", ""))
    if client is None:
        return {**state, "errors": state.get("errors", []) + [{"execute": "no client"}]}
    approval_id = state.get("pending_approval_id")
    if not approval_id:
        return {**state, "errors": state.get("errors", []) + [{"execute": "no approval id"}]}

    idem = "idem-" + uuid4().hex[:12]
    res = await client.call_tool("leads_confirm_create", {
        "approval_id": approval_id, "idempotency_key": idem,
    })
    if not res.get("ok"):
        return {**state, "errors": state.get("errors", []) + [{"execute": res.get("error", {})}]}

    data = res["data"]
    lead_id = data.get("lead_id")
    state["lead_reference"] = data.get("public_reference")

    # Optional callback scheduling (if requested)
    facts = state.get("facts", {})
    if state.get("intent") in {"callback_request", "enroll"} and facts.get("batch_id"):
        from datetime import datetime, timedelta, timezone

        from packages.contracts.domain import CallbackWindow

        # Demo: schedule a callback the next day 19:00 local
        start = datetime.now(timezone.utc) + timedelta(days=1)
        start = start.replace(hour=13, minute=30, second=0, microsecond=0)  # 19:00 IST approx
        window = CallbackWindow(
            start_at=start, end_at=start + timedelta(minutes=30),
            timezone=state.get("timezone", "UTC"),
        )
        cb_res = await client.call_tool("callbacks_schedule", {
            "lead_id": lead_id,
            "window": window.model_dump(mode="json"),
            "approval_id": approval_id,  # simplified: same approval for demo
            "idempotency_key": "cb-" + idem,
        })
        if cb_res.get("ok"):
            state["callback_reference"] = cb_res["data"].get("callback", {}).get("callback_id")
        else:
            state["errors"] = state.get("errors", []) + [{"callback": cb_res.get("error", {})}]

    return state


__all__ = ["execute_write"]