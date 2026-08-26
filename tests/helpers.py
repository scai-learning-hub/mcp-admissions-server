"""Helpers to build a minimal seeded DB session for tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from services.mcp_server.repositories.models import Batch, Course, FeePlan, Policy


def seed_minimal(session: Session) -> dict[str, str]:
    """Seed one course, one batch, one fee plan, one policy. Returns ids."""
    now = datetime.now(timezone.utc)
    course = Course(
        slug="agentic-ai",
        title="Agentic AI Engineering",
        level="advanced",
        duration_weeks=12,
        modes=["online", "hybrid"],
        status="published",
        description="Multi-agent AI systems.",
        topics=["agents", "LangGraph", "MCP"],
    )
    session.add(course)
    session.flush()

    batch = Batch(
        course_id=course.id,
        start_at=now + timedelta(days=10),
        timezone="Asia/Kolkata",
        mode="online",
        seats_total=20,
        seats_reserved=5,
        status="enrolling",
    )
    session.add(batch)
    session.flush()

    plan = FeePlan(
        course_id=course.id,
        currency="INR",
        base_amount=45000,
        installment_json={"count": 2},
        valid_from=now,
        valid_to=None,
        policy_version="1",
    )
    session.add(plan)

    session.add(Policy(
        slug="admissions",
        version="1",
        title="Admissions Policy",
        content_md="## Admissions\n- Consent required.\n- Quotes valid 1h.\n",
        effective_at=now,
        retired_at=None,
    ))
    session.commit()
    return {"course_id": course.id, "batch_id": batch.id, "fee_plan_id": plan.id}