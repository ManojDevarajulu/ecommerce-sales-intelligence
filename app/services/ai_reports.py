"""
app/services/ai_reports.py — deterministic statistics for the three
OpenRouter reports, plus each report's prompt template and its
deterministic fallback narrative.

The division of labour across the two service modules: everything here is
report-specific (which numbers to compute, how to phrase them, what to say
if the LLM is unavailable), while the generic call/parse/validate
machinery lives in `app/services/openrouter.py`.

Orders and ratings stats reuse the same raw-SQL-via-`run_query` pattern as
`app/api/analytics.py` — they are the same kind of aggregate query, just
consumed by an LLM prompt instead of returned to a caller. RFM is the
exception: quintile scoring is a per-customer statistical computation that
pandas expresses far more directly than hand-rolled SQL window functions,
the same tool choice already made for comparable work in `ml/train.py`.
"""
from datetime import date

import pandas as pd
from sqlalchemy.orm import Session

from app.db.session import engine
from app.schemas.ai_reports import (
    CategoryRevenueShare,
    CategoryReturnRate,
    OrdersStats,
    RatingsStats,
    RegionRevenueShare,
    SegmentSummary,
    SegmentsStats,
)
from app.schemas.ai_reports import ReportNarrative
from app.services.analytics import optional_where, run_query

# ----------------------------------------------------------------------------
# Orders report: deterministic stats aggregator
# ----------------------------------------------------------------------------
def compute_orders_stats(db: Session, date_from: date | None, date_to: date | None) -> OrdersStats:
    where_sql, params = optional_where(
        ("order_date >= :date_from", "date_from", date_from),
        ("order_date <= :date_to", "date_to", date_to),
    )
    totals = run_query(
        db,
        f"""
        SELECT COUNT(*) AS order_count, SUM(net_sales) AS total_revenue,
               ROUND(AVG(net_sales), 2) AS avg_order_value,
               ROUND(100.0 * COUNT(*) FILTER (WHERE return_status IS NOT NULL) / COUNT(*), 2) AS return_rate_pct
        FROM orders {where_sql}
        """,
        params,
    )[0]

    # order_items/products don't have their own order_date - filter through orders (same pattern as
    # app/api/analytics.py's product_analytics endpoint).
    item_where_sql, item_params = optional_where(
        ("o.order_date >= :date_from", "date_from", date_from),
        ("o.order_date <= :date_to", "date_to", date_to),
    )
    category_rows = run_query(
        db,
        f"""
        SELECT p.product_category, SUM(oi.net_sales) AS total_revenue
        FROM order_items oi JOIN products p ON p.product_id = oi.product_id
        JOIN orders o ON o.order_id = oi.order_id
        {item_where_sql}
        GROUP BY p.product_category ORDER BY total_revenue DESC LIMIT 3
        """,
        item_params,
    )
    region_rows = run_query(
        db,
        f"""
        SELECT region, SUM(net_sales) AS total_revenue
        FROM orders {where_sql}
        GROUP BY region ORDER BY total_revenue DESC LIMIT 3
        """,
        params,
    )
    channel_rows = run_query(
        db,
        f"""
        SELECT sales_channel, SUM(net_sales) AS total_revenue
        FROM orders {where_sql}
        GROUP BY sales_channel ORDER BY total_revenue DESC LIMIT 1
        """,
        params,
    )

    total_revenue = totals["total_revenue"] or 0
    return OrdersStats(
        date_from=date_from,
        date_to=date_to,
        order_count=totals["order_count"],
        total_revenue=total_revenue,
        avg_order_value=totals["avg_order_value"] or 0,
        return_rate_pct=totals["return_rate_pct"] or 0,
        top_categories=[
            CategoryRevenueShare(
                product_category=r["product_category"], total_revenue=r["total_revenue"],
                share_pct=round(100 * float(r["total_revenue"]) / float(total_revenue), 2) if total_revenue else 0,
            )
            for r in category_rows
        ],
        top_regions=[
            RegionRevenueShare(
                region=r["region"], total_revenue=r["total_revenue"],
                share_pct=round(100 * float(r["total_revenue"]) / float(total_revenue), 2) if total_revenue else 0,
            )
            for r in region_rows
        ],
        top_channel=channel_rows[0]["sales_channel"] if channel_rows else None,
        top_channel_revenue=channel_rows[0]["total_revenue"] if channel_rows else None,
    )


def orders_report_prompt(stats: OrdersStats) -> str:
    return f"""You are a retail analytics assistant. Write a business narrative for this e-commerce orders \
report. Use ONLY the numbers below - do not invent or estimate any figure not given here.

Period: {stats.date_from or 'all time'} to {stats.date_to or 'all time'}
Total orders: {stats.order_count:,}
Total revenue: ${stats.total_revenue:,.2f}
Average order value: ${stats.avg_order_value:,.2f}
Return rate: {stats.return_rate_pct}%
Top categories by revenue: {[(c.product_category, f"${c.total_revenue:,.2f} ({c.share_pct}%)") for c in stats.top_categories]}
Top regions by revenue: {[(r.region, f"${r.total_revenue:,.2f} ({r.share_pct}%)") for r in stats.top_regions]}
Top sales channel: {stats.top_channel} (${stats.top_channel_revenue:,.2f})"""


def orders_report_fallback(stats: OrdersStats) -> ReportNarrative:
    top_cat = stats.top_categories[0].product_category if stats.top_categories else "N/A"
    top_region = stats.top_regions[0].region if stats.top_regions else "N/A"
    return ReportNarrative(
        summary=f"{stats.order_count:,} orders generated ${stats.total_revenue:,.2f} in revenue "
                f"(AOV ${stats.avg_order_value:,.2f}) with a {stats.return_rate_pct}% return rate.",
        key_insights=[
            f"'{top_cat}' is the top-revenue category"
            + (f" at {stats.top_categories[0].share_pct}% of total revenue." if stats.top_categories else "."),
            f"'{top_region}' is the top-revenue region"
            + (f" at {stats.top_regions[0].share_pct}% of total revenue." if stats.top_regions else "."),
            f"'{stats.top_channel}' is the leading sales channel by revenue." if stats.top_channel else
            "No sales-channel data available for this period.",
        ],
        recommendations=[
            f"Investigate the {stats.return_rate_pct}% return rate for cost-reduction opportunities.",
            f"Consider concentrating marketing spend toward '{top_region}' and '{top_cat}', the current "
            "top performers.",
        ],
    )


# ----------------------------------------------------------------------------
# Ratings report: deterministic stats aggregator
# ----------------------------------------------------------------------------
def compute_ratings_stats(db: Session, date_from: date | None, date_to: date | None) -> RatingsStats:
    order_where_sql, order_params = optional_where(
        ("o.order_date >= :date_from", "date_from", date_from),
        ("o.order_date <= :date_to", "date_to", date_to),
    )
    rating_summary = run_query(
        db,
        f"""
        SELECT COUNT(*) AS total_ratings, ROUND(AVG(r.rating), 2) AS avg_rating
        FROM ratings r JOIN orders o ON o.order_id = r.order_id {order_where_sql}
        """,
        order_params,
    )[0]
    distribution_rows = run_query(
        db,
        f"""
        SELECT r.rating, COUNT(*) AS num_ratings
        FROM ratings r JOIN orders o ON o.order_id = r.order_id {order_where_sql}
        GROUP BY r.rating ORDER BY r.rating
        """,
        order_params,
    )

    overall_where_sql, overall_params = optional_where(
        ("order_date >= :date_from", "date_from", date_from),
        ("order_date <= :date_to", "date_to", date_to),
    )
    overall_return = run_query(
        db,
        f"SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE return_status IS NOT NULL) / COUNT(*), 2) AS pct "
        f"FROM orders {overall_where_sql}",
        overall_params,
    )[0]["pct"]

    category_where_sql, category_params = optional_where(
        ("o.order_date >= :date_from", "date_from", date_from),
        ("o.order_date <= :date_to", "date_to", date_to),
    )
    category_return_rates = run_query(
        db,
        f"""
        SELECT p.product_category,
               ROUND(100.0 * COUNT(DISTINCT oi.order_id) FILTER (WHERE o.return_status IS NOT NULL)
                     / COUNT(DISTINCT oi.order_id), 2) AS return_rate_pct
        FROM order_items oi
        JOIN products p ON p.product_id = oi.product_id
        JOIN orders o ON o.order_id = oi.order_id
        {category_where_sql}
        GROUP BY p.product_category
        """,
        category_params,
    )
    by_rate = sorted(category_return_rates, key=lambda r: r["return_rate_pct"], reverse=True)

    return RatingsStats(
        date_from=date_from,
        date_to=date_to,
        total_ratings=rating_summary["total_ratings"] or 0,
        avg_rating=rating_summary["avg_rating"] or 0,
        rating_distribution={str(r["rating"]): r["num_ratings"] for r in distribution_rows},
        overall_return_rate_pct=overall_return or 0,
        highest_return_rate_categories=[
            CategoryReturnRate(product_category=r["product_category"], return_rate_pct=r["return_rate_pct"])
            for r in by_rate[:3]
        ],
        lowest_return_rate_categories=[
            CategoryReturnRate(product_category=r["product_category"], return_rate_pct=r["return_rate_pct"])
            for r in by_rate[-3:][::-1]
        ],
    )


def ratings_report_prompt(stats: RatingsStats) -> str:
    return f"""You are a retail analytics assistant. Write a business narrative for this customer ratings & \
returns report. Use ONLY the numbers below - do not invent or estimate any figure not given here.

Period: {stats.date_from or 'all time'} to {stats.date_to or 'all time'}
Total ratings collected: {stats.total_ratings:,}
Average rating: {stats.avg_rating}/5
Rating distribution: {stats.rating_distribution}
Overall return rate: {stats.overall_return_rate_pct}%
Highest-return-rate categories: {[(c.product_category, f"{c.return_rate_pct}%") for c in stats.highest_return_rate_categories]}
Lowest-return-rate categories: {[(c.product_category, f"{c.return_rate_pct}%") for c in stats.lowest_return_rate_categories]}"""


def ratings_report_fallback(stats: RatingsStats) -> ReportNarrative:
    highest = stats.highest_return_rate_categories[0] if stats.highest_return_rate_categories else None
    lowest = stats.lowest_return_rate_categories[0] if stats.lowest_return_rate_categories else None
    return ReportNarrative(
        summary=f"{stats.total_ratings:,} ratings collected, averaging {stats.avg_rating}/5, against an "
                f"overall return rate of {stats.overall_return_rate_pct}%.",
        key_insights=[
            f"'{highest.product_category}' has the highest return rate at {highest.return_rate_pct}%."
            if highest else "No category return-rate data available.",
            f"'{lowest.product_category}' has the lowest return rate at {lowest.return_rate_pct}%."
            if lowest else "No category return-rate data available.",
        ],
        recommendations=[
            f"Review product quality/listing accuracy for '{highest.product_category}'." if highest else
            "Collect more rating data before drawing category-level conclusions.",
        ],
    )


# ----------------------------------------------------------------------------
# Customer segmentation report: RFM computation
# ----------------------------------------------------------------------------
# Recency/Frequency/Monetary per customer, scored into quintiles (1=worst,
# 5=best on each dimension) and combined into a small set of standard,
# named segments - not the dataset's own `customer_segment` column (that's
# a separate, pre-assigned business label, not derived from behavior here).
# Recency is measured from the dataset's own max(order_date), not real
# wall-clock "now" - this is historical data (2021-2025), and "now" would
# make every customer look years inactive regardless of real behavior.
_SEGMENT_RULES: list[tuple[str, "callable"]] = [
    ("Champions", lambda r, f, m: r >= 4 and f >= 4 and m >= 4),
    ("Loyal", lambda r, f, m: f >= 4),
    ("At Risk", lambda r, f, m: r <= 2 and (f >= 3 or m >= 3)),
    ("New", lambda r, f, m: f == 1 and r >= 4),
    ("Lost", lambda r, f, m: r <= 2 and f <= 2 and m <= 2),
]
_DEFAULT_SEGMENT = "Needs Attention"


def _assign_segment(r: int, f: int, m: int) -> str:
    for name, rule in _SEGMENT_RULES:
        if rule(r, f, m):
            return name
    return _DEFAULT_SEGMENT


def compute_rfm_and_segments() -> SegmentsStats:
    orders = pd.read_sql("SELECT customer_id, order_date, net_sales FROM orders", engine)
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    as_of = orders["order_date"].max()

    rfm = orders.groupby("customer_id").agg(
        last_order_date=("order_date", "max"),
        frequency=("order_date", "count"),
        monetary=("net_sales", "sum"),
    )
    rfm["recency_days"] = (as_of - rfm["last_order_date"]).dt.days

    # `qcut` always assigns label 1 to the smallest-RANK bin and label 5 to
    # the largest, regardless of `.rank()`'s own `ascending` flag - that
    # flag only controls which raw values get small vs. large ranks. So to
    # get "the best raw value -> score 5", the best raw value must be the
    # one that receives the LARGEST rank: `ascending=False` sends the
    # largest raw value to rank 1 (so the SMALLEST raw value gets the
    # largest rank) - exactly what recency needs (fewest days = best,
    # so days must be ranked with the biggest values first). Frequency/
    # monetary need the opposite (`ascending=True`: smallest raw value ->
    # rank 1, so the biggest count/spend gets the largest rank -> score 5).
    # This direction was verified against a toy series before being trusted
    # on real data, rather than just reasoned through: a first attempt had
    # the ranking inverted, which produced Champions with the WORST average
    # recency and Lost/At Risk with the best - plausible-looking output that
    # was exactly backwards.
    def score(series: pd.Series, ascending: bool) -> pd.Series:
        ranks = series.rank(method="first", ascending=ascending)
        return pd.qcut(ranks, 5, labels=[1, 2, 3, 4, 5]).astype(int)

    rfm["r_score"] = score(rfm["recency_days"], ascending=False)  # fewer days = more recent = higher score
    rfm["f_score"] = score(rfm["frequency"], ascending=True)  # more orders = higher score
    rfm["m_score"] = score(rfm["monetary"], ascending=True)  # more spend = higher score

    rfm["segment"] = [
        _assign_segment(r, f, m) for r, f, m in zip(rfm["r_score"], rfm["f_score"], rfm["m_score"])
    ]

    summary = rfm.groupby("segment").agg(
        customer_count=("segment", "size"),
        total_monetary=("monetary", "sum"),
        avg_recency_days=("recency_days", "mean"),
        avg_frequency=("frequency", "mean"),
    ).sort_values("total_monetary", ascending=False)

    return SegmentsStats(
        as_of_date=as_of.date(),
        total_customers_scored=len(rfm),
        segments=[
            SegmentSummary(
                segment=segment,
                customer_count=int(row["customer_count"]),
                total_monetary=round(float(row["total_monetary"]), 2),
                avg_recency_days=round(float(row["avg_recency_days"]), 1),
                avg_frequency=round(float(row["avg_frequency"]), 2),
            )
            for segment, row in summary.iterrows()
        ],
    )


def segments_report_prompt(stats: SegmentsStats) -> str:
    return f"""You are a retail analytics assistant. Write a business narrative for this RFM (Recency/\
Frequency/Monetary) customer segmentation report. Use ONLY the numbers below - do not invent or estimate any \
figure not given here.

Analysis date: {stats.as_of_date} (the most recent order date in the dataset)
Total customers scored: {stats.total_customers_scored:,}
Segments: {[(s.segment, f"{s.customer_count} customers", f"${s.total_monetary:,.2f} total spend",
             f"avg recency {s.avg_recency_days}d", f"avg frequency {s.avg_frequency}") for s in stats.segments]}"""


def segments_report_fallback(stats: SegmentsStats) -> ReportNarrative:
    top_segment = stats.segments[0] if stats.segments else None
    return ReportNarrative(
        summary=f"{stats.total_customers_scored:,} customers scored via RFM as of {stats.as_of_date}, "
                f"split across {len(stats.segments)} segments.",
        key_insights=[
            f"'{top_segment.segment}' is the highest-value segment by total spend "
            f"(${top_segment.total_monetary:,.2f} across {top_segment.customer_count} customers)."
            if top_segment else "No segment data available.",
        ] + [
            f"'{s.segment}': {s.customer_count} customers, avg recency {s.avg_recency_days} days, "
            f"avg frequency {s.avg_frequency} orders."
            for s in stats.segments if s is not top_segment
        ][:3],
        recommendations=[
            "Prioritize retention offers for the 'At Risk' segment before they lapse into 'Lost'.",
            "Target the 'New' segment with onboarding/second-purchase incentives.",
        ],
    )
