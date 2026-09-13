"""
app/api/ai.py — the three OpenRouter business report endpoints and the RAG
assistant endpoint.

All four are POST even though none of them create or mutate a resource.
That is deliberate: each one triggers a real external LLM call, which
costs quota and is not free to repeat, unlike the analytics endpoints'
pure database reads. Modelling them as GETs would invite caching and
naive retries against a rate-limited third-party API.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ai_reports import OrdersReportResponse, RatingsReportResponse, SegmentsReportResponse
from app.schemas.rag import RagQueryRequest, RagQueryResponse
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
from app.services.rag import answer_question
from rag.embeddings import EmbeddingError

router = APIRouter(prefix="/ai/reports", tags=["ai-reports"])
rag_router = APIRouter(prefix="/ai/rag", tags=["ai-rag"])


@router.post("/orders", response_model=OrdersReportResponse)
def orders_report(
    date_from: date | None = Query(None, description="order_date >= this date"),
    date_to: date | None = Query(None, description="order_date <= this date"),
    db: Session = Depends(get_db),
) -> OrdersReportResponse:
    """Order analysis report: sales performance, trends, top categories and
    regions, with an LLM-written narrative over deterministic figures."""
    stats = compute_orders_stats(db, date_from, date_to)
    narrative, meta = generate_narrative(orders_report_prompt(stats), orders_report_fallback(stats))
    return OrdersReportResponse(stats=stats, narrative=narrative, meta=meta)


@router.post("/customer-ratings", response_model=RatingsReportResponse)
def customer_ratings_report(
    date_from: date | None = Query(None, description="order_date >= this date"),
    date_to: date | None = Query(None, description="order_date <= this date"),
    db: Session = Depends(get_db),
) -> RatingsReportResponse:
    """Customer rating report: rating distribution and the categories with
    the highest and lowest return rates, narrated by the LLM."""
    stats = compute_ratings_stats(db, date_from, date_to)
    narrative, meta = generate_narrative(ratings_report_prompt(stats), ratings_report_fallback(stats))
    return RatingsReportResponse(stats=stats, narrative=narrative, meta=meta)


@router.post("/customer-segments", response_model=SegmentsReportResponse)
def customer_segments_report() -> SegmentsReportResponse:
    """RFM customer segmentation report.

    No date filters, unlike the other two reports: recency is measured
    against the dataset's own latest order date, so a date-windowed version
    would quietly redefine what "recent" means and mislead the caller.

    No `db: Session` dependency either — `compute_rfm_and_segments()` runs
    a single dataset-wide aggregation through pandas on the shared engine
    rather than a request-scoped ORM session, the same tool choice made for
    the equivalent statistical work in `ml/train.py`.
    """
    stats = compute_rfm_and_segments()
    narrative, meta = generate_narrative(segments_report_prompt(stats), segments_report_fallback(stats))
    return SegmentsReportResponse(stats=stats, narrative=narrative, meta=meta)


@rag_router.post("/query", response_model=RagQueryResponse)
def rag_query(body: RagQueryRequest, db: Session = Depends(get_db)) -> RagQueryResponse:
    """Grounded Q&A over the knowledge base in `rag/documents/`.

    See `app/services/rag.py` for response resolution states. On HTTP status codes:
    a query outside the knowledge base coverage returns 200 with `answered: false`
    and an insufficient data notification, indicating successful guardrail evaluation.

    If the upstream embedding service is unreachable, a 503 Service Unavailable
    is returned representing the upstream dependency outage.
    """
    try:
        return answer_question(body.question, db, top_k=body.top_k)
    except EmbeddingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"embedding service unavailable: {exc}",
        ) from exc
