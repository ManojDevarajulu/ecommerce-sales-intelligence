"""
app/schemas/ai_reports.py — T119/T122/T125: request/response schemas for the
3 OpenRouter business reports.

`ReportNarrative` is the one piece of every report that actually comes from
the LLM (or the deterministic fallback, T117, which fills the identical
shape) — every other field is deterministic SQL/Python (SCOPE.md's locked
rule for this phase). Keeping `stats` alongside `narrative` in every
response (not narrative alone) means the real numbers are sitting right
next to the LLM's prose, so a mismatch is checkable, not just asserted.
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class ReportNarrative(BaseModel):
    """What the LLM (or T117's deterministic fallback) produces — never the
    numbers themselves, only synthesis over numbers already computed."""

    summary: str = Field(..., description="1-2 sentence executive summary")
    key_insights: list[str] = Field(..., description="3-5 bullet-point observations grounded in `stats`")
    recommendations: list[str] = Field(..., description="2-4 actionable recommendations grounded in `stats`")


class ReportMeta(BaseModel):
    generated_by: str = Field(..., description="'openrouter' or 'deterministic_fallback'")
    model: str | None = Field(None, description="OpenRouter model id used, or null on fallback")


# ---------------------------------------------------------------- /orders
class CategoryRevenueShare(BaseModel):
    product_category: str
    total_revenue: Decimal
    share_pct: Decimal


class RegionRevenueShare(BaseModel):
    region: str
    total_revenue: Decimal
    share_pct: Decimal


class OrdersStats(BaseModel):
    date_from: date | None
    date_to: date | None
    order_count: int
    total_revenue: Decimal
    avg_order_value: Decimal
    return_rate_pct: Decimal
    top_categories: list[CategoryRevenueShare]
    top_regions: list[RegionRevenueShare]
    top_channel: str | None
    top_channel_revenue: Decimal | None


class OrdersReportResponse(BaseModel):
    stats: OrdersStats
    narrative: ReportNarrative
    meta: ReportMeta


# ------------------------------------------------------- /customer-ratings
class CategoryReturnRate(BaseModel):
    product_category: str
    return_rate_pct: Decimal


class RatingsStats(BaseModel):
    date_from: date | None
    date_to: date | None
    total_ratings: int
    avg_rating: Decimal
    rating_distribution: dict[str, int]
    overall_return_rate_pct: Decimal
    highest_return_rate_categories: list[CategoryReturnRate]
    lowest_return_rate_categories: list[CategoryReturnRate]


class RatingsReportResponse(BaseModel):
    stats: RatingsStats
    narrative: ReportNarrative
    meta: ReportMeta


# ------------------------------------------------------- /customer-segments
class SegmentSummary(BaseModel):
    segment: str
    customer_count: int
    total_monetary: Decimal
    avg_recency_days: Decimal
    avg_frequency: Decimal


class SegmentsStats(BaseModel):
    as_of_date: date = Field(..., description="Recency is computed relative to this date - the dataset's "
                                               "own max(order_date), not wall-clock 'now' (historical data).")
    total_customers_scored: int
    segments: list[SegmentSummary]


class SegmentsReportResponse(BaseModel):
    stats: SegmentsStats
    narrative: ReportNarrative
    meta: ReportMeta
