"""initial schema - all core tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("duration_weeks", sa.Integer, nullable=False),
        sa.Column("modes", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(20), nullable=False, server_default="published"),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("topics", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("row_version", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_index("ix_courses_slug", "courses", ["slug"], unique=True)
    op.create_index("ix_courses_level", "courses", ["level"])
    op.create_index("ix_courses_status", "courses", ["status"])

    op.create_table(
        "batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("seats_total", sa.Integer, nullable=False),
        sa.Column("seats_reserved", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="enrolling"),
        sa.Column("row_version", sa.Integer, nullable=False, server_default="1"),
        sa.CheckConstraint("seats_total >= 0", name="ck_batches_seats_total_nonneg"),
        sa.CheckConstraint("seats_reserved >= 0", name="ck_batches_seats_reserved_nonneg"),
        sa.CheckConstraint("seats_reserved <= seats_total", name="ck_batches_reserved_le_total"),
    )
    op.create_index("ix_batches_course_id", "batches", ["course_id"])
    op.create_index("ix_batches_start_at", "batches", ["start_at"])
    op.create_index("ix_batches_mode", "batches", ["mode"])
    op.create_index("ix_batches_status", "batches", ["status"])

    op.create_table(
        "fee_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("currency", sa.String(4), nullable=False, server_default="INR"),
        sa.Column("base_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("installment_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("policy_version", sa.String(40), nullable=False, server_default="1"),
    )
    op.create_index("ix_fee_plans_course_id", "fee_plans", ["course_id"])

    op.create_table(
        "fee_quotes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(120), nullable=False),
        sa.Column("course_id", sa.String(36), nullable=False),
        sa.Column("batch_id", sa.String(36), nullable=False),
        sa.Column("currency", sa.String(4), nullable=False, server_default="INR"),
        sa.Column("amount_json", postgresql.JSONB, nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_version", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_fee_quotes_actor_id", "fee_quotes", ["actor_id"])
    op.create_index("ix_fee_quotes_course_id", "fee_quotes", ["course_id"])
    op.create_index("ix_fee_quotes_batch_id", "fee_quotes", ["batch_id"])

    op.create_table(
        "policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content_md", sa.Text, nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("slug", "version", name="uq_policies_slug_version"),
    )
    op.create_index("ix_policies_slug", "policies", ["slug"])

    op.create_table(
        "lead_approvals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(120), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("preview_json", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_lead_approvals_actor_id", "lead_approvals", ["actor_id"])
    op.create_index("ix_lead_approvals_payload_hash", "lead_approvals", ["payload_hash"])
    op.create_index("ix_lead_approvals_status", "lead_approvals", ["status"])

    op.create_table(
        "leads",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("public_reference", sa.String(20), nullable=False, unique=True),
        sa.Column("contact_ciphertext", sa.Text, nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("course_id", sa.String(36), nullable=False),
        sa.Column("batch_id", sa.String(36), nullable=True),
        sa.Column("stage", sa.String(20), nullable=False, server_default="new"),
        sa.Column("assigned_to", sa.String(120), nullable=True),
        sa.Column("last_stage_note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("row_version", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_index("ix_leads_public_reference", "leads", ["public_reference"], unique=True)
    op.create_index("ix_leads_course_id", "leads", ["course_id"])
    op.create_index("ix_leads_batch_id", "leads", ["batch_id"])
    op.create_index("ix_leads_stage", "leads", ["stage"])
    op.create_index("ix_leads_assigned_to", "leads", ["assigned_to"])
    op.create_index("ix_leads_assigned_stage", "leads", ["assigned_to", "stage"])

    op.create_table(
        "callbacks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("lead_id", sa.String(36), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requested_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("assigned_to", sa.String(120), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="requested"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("row_version", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_index("ix_callbacks_lead_id", "callbacks", ["lead_id"])
    op.create_index("ix_callbacks_batch_id", "callbacks", ["batch_id"])
    op.create_index("ix_callbacks_status", "callbacks", ["status"])

    op.create_table(
        "tool_audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.String(120), nullable=False),
        sa.Column("actor_id", sa.String(120), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("tool_name", sa.String(80), nullable=False),
        sa.Column("args_hash", sa.String(64), nullable=False),
        sa.Column("result_code", sa.String(40), nullable=False),
        sa.Column("latency_ms", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tool_audit_events_trace_id", "tool_audit_events", ["trace_id"])
    op.create_index("ix_tool_audit_events_actor_id", "tool_audit_events", ["actor_id"])
    op.create_index("ix_tool_audit_events_tool_name", "tool_audit_events", ["tool_name"])
    op.create_index("ix_tool_audit_events_created_at", "tool_audit_events", ["created_at"])
    op.create_index("ix_audit_tool_created", "tool_audit_events", ["tool_name", "created_at"])

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(120), nullable=False),
        sa.Column("tool_name", sa.String(80), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("result_reference", sa.String(120), nullable=False),
        sa.Column("result_payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("actor_id", "tool_name", "idempotency_key", name="uq_idempotency_actor_tool_key"),
    )
    op.create_index("ix_idempotency_records_actor_id", "idempotency_records", ["actor_id"])
    op.create_index("ix_idempotency_records_tool_name", "idempotency_records", ["tool_name"])


def downgrade() -> None:
    op.drop_table("idempotency_records")
    op.drop_table("tool_audit_events")
    op.drop_table("callbacks")
    op.drop_table("leads")
    op.drop_table("lead_approvals")
    op.drop_table("policies")
    op.drop_table("fee_quotes")
    op.drop_table("fee_plans")
    op.drop_table("batches")
    op.drop_table("courses")