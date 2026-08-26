"""Fee domain service — deterministic quote generation.

A fee quote stores the exact fee and policy version used when it was created
(plan §8). The quote is source-of-truth: a client can only display a fee that
the server minted and versioned.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from packages.contracts.domain import FeeQuote, QuoteLineItem
from packages.contracts.error_codes import ErrorCode
from services.mcp_server.config import settings
from services.mcp_server.repositories.batches import BatchRepository
from services.mcp_server.repositories.courses import CourseRepository
from services.mcp_server.repositories.fees import FeePlanRepository, FeeQuoteRepository
from services.mcp_server.repositories.models import FeeQuote as FeeQuoteRow


class FeeService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.plans = FeePlanRepository(session)
        self.quotes = FeeQuoteRepository(session)
        self.courses = CourseRepository(session)
        self.batches = BatchRepository(session)

    def create_quote(
        self,
        *,
        actor_id: str,
        course_id: str,
        batch_id: str,
        currency: str = "INR",
    ) -> FeeQuote | tuple[ErrorCode, str]:
        # Validate course exists
        if self.courses.get_by_id(course_id) is None:
            return (ErrorCode.COURSE_NOT_FOUND, f"Course {course_id} not found.")
        # Validate batch exists and belongs to course
        batch = self.batches.get_by_id(batch_id)
        if batch is None or batch.course_id != course_id:
            return (ErrorCode.BATCH_NOT_AVAILABLE, "Batch not available for this course.")
        # Validate fee plan
        plan = self.plans.current_plan(course_id, currency=currency)
        if plan is None:
            return (
                ErrorCode.DEPENDENCY_UNAVAILABLE,
                f"No active fee plan for course {course_id} in {currency}.",
            )

        # Build line items deterministically from the plan.
        base = Decimal(str(plan.base_amount))
        gst_rate = Decimal("0.18")
        gst = (base * gst_rate).quantize(Decimal("0.01"))
        total = (base + gst).quantize(Decimal("0.01"))
        line_items = [
            QuoteLineItem(label="Tuition", amount=base, note="Base tuition fee"),
            QuoteLineItem(label="GST (18%)", amount=gst, note="Applicable tax"),
        ]
        # Installments metadata (if any) — kept as a non-amount note line
        installments = plan.installment_json or {}
        if installments:
            line_items.append(
                QuoteLineItem(
                    label="Installment plan",
                    amount=Decimal("0.00"),
                    note=str(installments),
                )
            )

        valid_until = datetime.now(timezone.utc) + timedelta(seconds=settings.quote_ttl_seconds)
        row = FeeQuoteRow(
            actor_id=actor_id,
            course_id=course_id,
            batch_id=batch_id,
            currency=currency,
            amount_json={
                "line_items": [li.model_dump(mode="json") for li in line_items],
                "installment_json": installments,
            },
            total=total,
            valid_until=valid_until,
            source_version=plan.policy_version,
        )
        self.quotes.create(row)
        self.session.flush()

        return FeeQuote(
            quote_id=row.id,
            course_id=course_id,
            batch_id=batch_id,
            currency=currency,
            line_items=line_items,
            total=total,
            valid_until=valid_until,
            policy_version=plan.policy_version,
            source_version=plan.policy_version,
        )


__all__ = ["FeeService"]