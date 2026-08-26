"""Seed demo data into PostgreSQL.

Uses synthetic contacts only (plan §8). Run AFTER `alembic upgrade head`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services.mcp_server.repositories.db import get_engine, session_scope
from services.mcp_server.repositories.models import (
    Batch,
    Course,
    FeePlan,
    Policy,
)


def seed() -> None:
    # Ensure schema exists (alembic should have run, but be defensive)
    from services.mcp_server.repositories.models import Base

    Base.metadata.create_all(get_engine())

    now = datetime.now(timezone.utc)

    courses = [
        Course(
            slug="agentic-ai",
            title="Agentic AI Engineering",
            level="advanced",
            duration_weeks=12,
            modes=["online", "hybrid"],
            status="published",
            description="Design, build, and govern multi-agent AI systems with LangGraph, MCP, and production guardrails.",
            topics=["agents", "LangGraph", "MCP", "tool use", "evals", "guardrails"],
        ),
        Course(
            slug="aiops",
            title="AIOps & MLOps",
            level="intermediate",
            duration_weeks=10,
            modes=["online"],
            status="published",
            description="Operate ML and AI systems in production: pipelines, observability, incident response.",
            topics=["MLOps", "LLMOps", "AgentOps", "observability"],
        ),
        Course(
            slug="mlops",
            title="MLOps Engineering",
            level="intermediate",
            duration_weeks=8,
            modes=["online", "in_person"],
            status="published",
            description="Production ML: CI/CD, registries, drift, rollback.",
            topics=["CI/CD", "model registry", "drift"],
        ),
        Course(
            slug="gen-ai",
            title="Generative AI Foundations",
            level="foundational",
            duration_weeks=6,
            modes=["online"],
            status="published",
            description="LLMs, prompting, RAG, and responsible AI basics.",
            topics=["LLM", "prompting", "RAG"],
        ),
    ]

    with session_scope() as sess:
        # Wipe demo data (idempotent re-seed)
        sess.query(Batch).delete()
        sess.query(FeePlan).delete()
        sess.query(Policy).delete()
        sess.query(Course).delete()
        sess.flush()

        for c in courses:
            sess.add(c)
        sess.flush()

        # Batches for agentic-ai
        agentic = next(c for c in courses if c.slug == "agentic-ai")
        batches = [
            Batch(
                course_id=agentic.id,
                start_at=now + timedelta(days=10, hours=0),
                timezone="Asia/Kolkata",
                mode="online",
                seats_total=30,
                seats_reserved=12,
                status="enrolling",
            ),
            Batch(
                course_id=agentic.id,
                start_at=now + timedelta(days=24, hours=0),
                timezone="Asia/Kolkata",
                mode="hybrid",
                seats_total=20,
                seats_reserved=5,
                status="enrolling",
            ),
            Batch(
                course_id=agentic.id,
                start_at=now + timedelta(days=60, hours=0),
                timezone="Asia/Kolkata",
                mode="online",
                seats_total=30,
                seats_reserved=0,
                status="scheduled",
            ),
        ]
        # A batch for aiops
        aiops = next(c for c in courses if c.slug == "aiops")
        batches.append(
            Batch(
                course_id=aiops.id,
                start_at=now + timedelta(days=15),
                timezone="Asia/Kolkata",
                mode="online",
                seats_total=25,
                seats_reserved=8,
                status="enrolling",
            )
        )
        for b in batches:
            sess.add(b)
        sess.flush()

        # Fee plans
        for c in courses:
            sess.add(FeePlan(
                course_id=c.id,
                currency="INR",
                base_amount=45000 if c.level == "advanced" else 35000 if c.level == "intermediate" else 25000,
                installment_json={"count": 2, "first": 50, "second": 50},
                valid_from=now,
                valid_to=None,
                policy_version="1",
            ))
        sess.flush()

        # Policies
        sess.add(Policy(
            slug="admissions",
            version="1",
            title="Admissions Policy",
            content_md=(
                "## Admissions Policy (v1)\n\n"
                "- A confirmed lead requires explicit user consent.\n"
                "- Fee quotes are valid for 1 hour from issuance.\n"
                "- Seat reservation is transactional; seats cannot go negative.\n"
                "- Callbacks are requested, not guaranteed, and assigned by queue.\n"
            ),
            effective_at=now,
            retired_at=None,
        ))
        sess.add(Policy(
            slug="refund",
            version="1",
            title="Refund Policy",
            content_md="## Refund Policy (v1)\n\nFull refund within 7 days of batch start. No refund thereafter.\n",
            effective_at=now,
            retired_at=None,
        ))
        sess.add(Policy(
            slug="privacy",
            version="1",
            title="Privacy Policy",
            content_md="## Privacy Policy (v1)\n\nContact data is encrypted at rest and never exposed via tool outputs.\n",
            effective_at=now,
            retired_at=None,
        ))

    print("Seed complete: 4 courses, 4 batches, 4 fee plans, 3 policies.")


if __name__ == "__main__":
    seed()