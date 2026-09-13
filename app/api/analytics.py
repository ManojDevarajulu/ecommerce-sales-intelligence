"""
app/api/analytics.py — the six analytics endpoints.

Each one wraps queries from `sql/02_analytics_queries.sql` (Q1-Q11) and
adds optional date/region/category filtering on top, through
`optional_where` in `app/services/analytics.py`.

The SQL is intentionally kept close to the standalone query file rather
than rewritten in the ORM: those queries were reconciled against the
dataset's own published totals, and keeping the two in the same shape
means a figure from the API can be checked against the figure from the
SQL file without translating between two dialects.
"""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analytics import (
    CustomerAnalyticsResponse,
    MarketingAnalyticsResponse,
    ProductAnalyticsResponse,
    RatingAnalyticsResponse,
    RegionAnalyticsResponse,
    SalesAnalyticsResponse,
)
from app.schemas.enums import ProductCategory, Region
from app.services.analytics import optional_where, run_query

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/sales", response_model=SalesAnalyticsResponse)
def sales_analytics(
    date_from: date | None = Query(None, description="order_date >= this date"),
    date_to: date | None = Query(None, description="order_date <= this date"),
    region: Region | None = Query(None, description="Filter to one region"),
    db: Session = Depends(get_db),
) -> SalesAnalyticsResponse:
    """Monthly revenue trend (Q3) and yearly revenue with YoY growth (Q4)."""
    where_sql, params = optional_where(
        ("order_date >= :date_from", "date_from", date_from),
        ("order_date <= :date_to", "date_to", date_to),
        ("region = :region", "region", region.value if region else None),
    )

    monthly = run_query(
        db,
        f"""
        SELECT date_trunc('month', order_date)::date AS month,
               COUNT(*) AS order_count, SUM(net_sales) AS total_revenue
        FROM orders {where_sql}
        GROUP BY 1 ORDER BY 1
        """,
        params,
    )

    yearly = run_query(
        db,
        f"""
        WITH yearly AS (
            SELECT EXTRACT(YEAR FROM order_date)::int AS year, SUM(net_sales) AS total_revenue
            FROM orders {where_sql}
            GROUP BY 1
        )
        SELECT year, total_revenue,
               ROUND(100.0 * (total_revenue - LAG(total_revenue) OVER (ORDER BY year))
                     / NULLIF(LAG(total_revenue) OVER (ORDER BY year), 0), 2) AS yoy_growth_pct
        FROM yearly ORDER BY year
        """,
        params,
    )
    return SalesAnalyticsResponse(monthly=monthly, yearly=yearly)


@router.get("/customers", response_model=CustomerAnalyticsResponse)
def customer_analytics(
    region: Region | None = Query(None, description="Filter by customer region"),
    customer_segment: str | None = Query(None, description="Filter by customer segment"),
    limit: int = Query(10, ge=1, le=100, description="Top N customers by revenue"),
    db: Session = Depends(get_db),
) -> CustomerAnalyticsResponse:
    """Top customers by revenue (Q1)."""
    where_sql, params = optional_where(
        ("c.region = :region", "region", region.value if region else None),
        ("c.customer_segment = :customer_segment", "customer_segment", customer_segment),
    )
    params["limit"] = limit

    top_customers = run_query(
        db,
        f"""
        SELECT c.customer_id, c.customer_name, c.customer_segment, c.region,
               COUNT(o.order_id) AS order_count, SUM(o.net_sales) AS total_revenue,
               ROUND(AVG(o.net_sales), 2) AS avg_order_value
        FROM customers c JOIN orders o ON o.customer_id = c.customer_id
        {where_sql}
        GROUP BY c.customer_id, c.customer_name, c.customer_segment, c.region
        ORDER BY total_revenue DESC
        LIMIT :limit
        """,
        params,
    )
    return CustomerAnalyticsResponse(top_customers=top_customers)


@router.get("/products", response_model=ProductAnalyticsResponse)
def product_analytics(
    product_category: ProductCategory | None = Query(None, description="Filter by category"),
    date_from: date | None = Query(None, description="order_date >= this date"),
    date_to: date | None = Query(None, description="order_date <= this date"),
    limit: int = Query(10, ge=1, le=100, description="Top N products by revenue"),
    db: Session = Depends(get_db),
) -> ProductAnalyticsResponse:
    """Top products by revenue (Q2) and revenue/margin by category (Q5).

    Both queries join `orders` (not just `order_items`) so `date_from`/
    `date_to` can filter them the same way as every other endpoint.
    """
    where_sql, params = optional_where(
        ("p.product_category = :product_category", "product_category",
         product_category.value if product_category else None),
        ("o.order_date >= :date_from", "date_from", date_from),
        ("o.order_date <= :date_to", "date_to", date_to),
    )

    top_products = run_query(
        db,
        f"""
        SELECT p.product_id, p.product_name, p.product_category,
               SUM(oi.quantity) AS units_sold, SUM(oi.net_sales) AS total_revenue
        FROM products p
        JOIN order_items oi ON oi.product_id = p.product_id
        JOIN orders o ON o.order_id = oi.order_id
        {where_sql}
        GROUP BY p.product_id, p.product_name, p.product_category
        ORDER BY total_revenue DESC
        LIMIT :limit
        """,
        {**params, "limit": limit},
    )

    by_category = run_query(
        db,
        f"""
        SELECT p.product_category, SUM(oi.net_sales) AS total_revenue, SUM(oi.profit) AS total_profit,
               ROUND(100.0 * SUM(oi.profit) / NULLIF(SUM(oi.net_sales), 0), 2) AS margin_pct
        FROM order_items oi
        JOIN products p ON p.product_id = oi.product_id
        JOIN orders o ON o.order_id = oi.order_id
        {where_sql}
        GROUP BY p.product_category
        ORDER BY total_revenue DESC
        """,
        params,
    )
    return ProductAnalyticsResponse(top_products=top_products, by_category=by_category)


@router.get("/regions", response_model=RegionAnalyticsResponse)
def region_analytics(
    date_from: date | None = Query(None, description="order_date >= this date"),
    date_to: date | None = Query(None, description="order_date <= this date"),
    db: Session = Depends(get_db),
) -> RegionAnalyticsResponse:
    """Revenue and fulfillment performance by region (Q6).

    See `sql/02_analytics_queries.sql`'s Q6 comment: `delivery_status =
    'Cancelled'` bundles true cancellations, pending orders, AND returns
    together in this dataset — `cancelled_pending_or_returned_pct` is named
    accordingly, not just "cancelled_pct".
    """
    where_sql, params = optional_where(
        ("order_date >= :date_from", "date_from", date_from),
        ("order_date <= :date_to", "date_to", date_to),
    )

    regions = run_query(
        db,
        f"""
        SELECT region, COUNT(*) AS order_count, SUM(net_sales) AS total_revenue,
               ROUND(100.0 * COUNT(*) FILTER (WHERE delivery_status = 'On Time') / COUNT(*), 2) AS on_time_pct,
               ROUND(100.0 * COUNT(*) FILTER (WHERE delivery_status = 'Delayed') / COUNT(*), 2) AS delayed_pct,
               ROUND(100.0 * COUNT(*) FILTER (WHERE delivery_status = 'Early') / COUNT(*), 2) AS early_pct,
               ROUND(100.0 * COUNT(*) FILTER (WHERE delivery_status = 'Cancelled') / COUNT(*), 2)
                   AS cancelled_pending_or_returned_pct
        FROM orders {where_sql}
        GROUP BY region ORDER BY total_revenue DESC
        """,
        params,
    )
    return RegionAnalyticsResponse(regions=regions)


@router.get("/marketing", response_model=MarketingAnalyticsResponse)
def marketing_analytics(
    date_from: date | None = Query(None, description="order_date >= this date"),
    date_to: date | None = Query(None, description="order_date <= this date"),
    db: Session = Depends(get_db),
) -> MarketingAnalyticsResponse:
    """Average order value by sales channel (Q7) and marketing-channel
    ROI (Q11).

    The date filter applies to Q7 directly, and to Q11's *lifetime revenue*
    window — but deliberately NOT to which channel a customer is attributed
    to (their first order's channel is a fixed, historical fact, not
    something that should change depending on the reporting window).
    """
    where_sql, params = optional_where(
        ("order_date >= :date_from", "date_from", date_from),
        ("order_date <= :date_to", "date_to", date_to),
    )

    channel_aov = run_query(
        db,
        f"""
        SELECT sales_channel, COUNT(*) AS order_count,
               ROUND(AVG(net_sales), 2) AS avg_order_value, SUM(net_sales) AS total_revenue
        FROM orders {where_sql}
        GROUP BY sales_channel ORDER BY total_revenue DESC
        """,
        params,
    )

    revenue_where_sql, revenue_params = optional_where(
        ("order_date >= :date_from", "date_from", date_from),
        ("order_date <= :date_to", "date_to", date_to),
    )
    channel_roi = run_query(
        db,
        f"""
        WITH first_order AS (
            SELECT DISTINCT ON (customer_id) customer_id, marketing_channel
            FROM orders
            WHERE marketing_channel IS NOT NULL
            ORDER BY customer_id, order_date ASC
        ),
        customer_revenue AS (
            SELECT customer_id, SUM(net_sales) AS lifetime_revenue
            FROM orders {revenue_where_sql}
            GROUP BY customer_id
        )
        SELECT fo.marketing_channel, COUNT(DISTINCT fo.customer_id) AS customers_acquired,
               SUM(cr.lifetime_revenue) AS lifetime_revenue,
               ROUND(SUM(c.customer_acquisition_cost), 2) AS total_acquisition_cost,
               ROUND(SUM(cr.lifetime_revenue) / NULLIF(SUM(c.customer_acquisition_cost), 0), 2)
                   AS revenue_per_acquisition_dollar
        FROM first_order fo
        JOIN customer_revenue cr ON cr.customer_id = fo.customer_id
        JOIN customers c ON c.customer_id = fo.customer_id
        GROUP BY fo.marketing_channel
        ORDER BY lifetime_revenue DESC
        """,
        revenue_params,
    )
    return MarketingAnalyticsResponse(channel_aov=channel_aov, channel_roi=channel_roi)


@router.get("/ratings", response_model=RatingAnalyticsResponse)
def rating_analytics(
    product_category: ProductCategory | None = Query(
        None, description="Filter the return-rate-by-category breakdown to one category"
    ),
    date_from: date | None = Query(None, description="order_date >= this date"),
    date_to: date | None = Query(None, description="order_date <= this date"),
    db: Session = Depends(get_db),
) -> RatingAnalyticsResponse:
    """Rating distribution and its delivery-status correlate (Q9), plus
    (return rate, overall and by category).

    `rating_distribution`/`rating_by_delivery_status` join through `orders`
    for the date filter; `product_category` only narrows the by-category
    return-rate breakdown, since ratings have no category dimension.
    """
    order_where_sql, order_params = optional_where(
        ("o.order_date >= :date_from", "date_from", date_from),
        ("o.order_date <= :date_to", "date_to", date_to),
    )

    rating_distribution = run_query(
        db,
        f"""
        SELECT r.rating, COUNT(*) AS num_ratings
        FROM ratings r JOIN orders o ON o.order_id = r.order_id
        {order_where_sql}
        GROUP BY r.rating ORDER BY r.rating
        """,
        order_params,
    )

    rating_by_delivery_status = run_query(
        db,
        f"""
        SELECT o.delivery_status, COUNT(r.rating) AS num_ratings, ROUND(AVG(r.rating), 2) AS avg_rating
        FROM orders o JOIN ratings r ON r.order_id = o.order_id
        {order_where_sql}
        GROUP BY o.delivery_status ORDER BY avg_rating DESC
        """,
        order_params,
    )

    overall_where_sql, overall_params = optional_where(
        ("order_date >= :date_from", "date_from", date_from),
        ("order_date <= :date_to", "date_to", date_to),
    )
    overall = run_query(
        db,
        f"""
        SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE return_status IS NOT NULL) / COUNT(*), 2)
            AS return_rate_pct
        FROM orders {overall_where_sql}
        """,
        overall_params,
    )

    category_where_sql, category_params = optional_where(
        ("p.product_category = :product_category", "product_category",
         product_category.value if product_category else None),
        ("o.order_date >= :date_from", "date_from", date_from),
        ("o.order_date <= :date_to", "date_to", date_to),
    )
    return_rate_by_category = run_query(
        db,
        f"""
        SELECT p.product_category,
               COUNT(DISTINCT oi.order_id) AS orders_with_category,
               COUNT(DISTINCT oi.order_id) FILTER (WHERE o.return_status IS NOT NULL) AS returned_orders,
               ROUND(100.0 * COUNT(DISTINCT oi.order_id) FILTER (WHERE o.return_status IS NOT NULL)
                     / COUNT(DISTINCT oi.order_id), 2) AS return_rate_pct
        FROM order_items oi
        JOIN products p ON p.product_id = oi.product_id
        JOIN orders o ON o.order_id = oi.order_id
        {category_where_sql}
        GROUP BY p.product_category
        ORDER BY return_rate_pct DESC
        """,
        category_params,
    )

    return RatingAnalyticsResponse(
        rating_distribution=rating_distribution,
        rating_by_delivery_status=rating_by_delivery_status,
        overall_return_rate_pct=overall[0]["return_rate_pct"],
        return_rate_by_category=return_rate_by_category,
    )
