"""
app/api/ai.py — T120/T123/T126: the 3 OpenRouter business report endpoints.

All POST (not GET) even though nothing is created/mutated - SCOPE.md's own
naming (`POST /ai/reports/...`) reflects that these trigger a real external
LLM call (a side-effecting, non-idempotent-cost action), unlike the
analytics endpoints' pure-DB reads.
"""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ai_reports import OrdersReportResponse, RatingsReportResponse, SegmentsReportResponse
from app.services.ai_reports import (
    compute_orders_stats,
    compute_ratings_stats,
    compute_rfm_and_segments,
    orders_report_fallback,
    orders_report_prompt,
    ratings_report_fallback,
    ratings_report_prompt,
    segments_report_fallback,
    segments_report_prompt,
)
from app.services.openrouter import generate_narrative

router = APIRouter(prefix="/ai/reports", tags=["ai-reports"])


@router.post("/orders", response_model=OrdersReportResponse)
def orders_report(
    date_from: date | None = Query(None, description="order_date >= this date"),
    date_to: date | None = Query(None, description="order_date <= this date"),
    db: Session = Depends(get_db),
) -> OrdersReportResponse:
    """T120."""
    stats = compute_orders_stats(db, date_from, date_to)
    narrative, meta = generate_narrative(orders_report_prompt(stats), orders_report_fallback(stats))
    return OrdersReportResponse(stats=stats, narrative=narrative, meta=meta)


@router.post("/customer-ratings", response_model=RatingsReportResponse)
def customer_ratings_report(
    date_from: date | None = Query(None, description="order_date >= this date"),
    date_to: date | None = Query(None, description="order_date <= this date"),
    db: Session = Depends(get_db),
) -> RatingsReportResponse:
    """T123."""
    stats = compute_ratings_stats(db, date_from, date_to)
    narrative, meta = generate_narrative(ratings_report_prompt(stats), ratings_report_fallback(stats))
    return RatingsReportResponse(stats=stats, narrative=narrative, meta=meta)


@router.post("/customer-segments", response_model=SegmentsReportResponse)
def customer_segments_report() -> SegmentsReportResponse:
    """T126. No date filters - unlike the other two reports, RFM recency is
    inherently relative to the dataset's own max(order_date) (T124), so a
    date-windowed version wouldn't mean what a caller would expect it to.
    No `db: Session` dependency either - `compute_rfm_and_segments()` uses
    the shared engine directly via pandas (see app/services/ai_reports.py),
    the same tool choice `ml/train.py` made for equivalent statistical work.
    """
    stats = compute_rfm_and_segments()
    narrative, meta = generate_narrative(segments_report_prompt(stats), segments_report_fallback(stats))
    return SegmentsReportResponse(stats=stats, narrative=narrative, meta=meta)
