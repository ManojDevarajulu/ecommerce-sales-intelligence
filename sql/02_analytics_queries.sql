-- ============================================================================
-- E-Commerce Sales Intelligence Platform - Analytics Queries
-- File: sql/02_analytics_queries.sql
-- All revenue/profit figures use net_sales (post-discount). That is this
-- dataset's own definition of revenue: summing gross_sales instead
-- overstates the published total by about 7%.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Q1: Top 10 customers by revenue
-- ----------------------------------------------------------------------------
SELECT
    c.customer_id,
    c.customer_name,
    c.customer_segment,
    c.region,
    COUNT(o.order_id)              AS order_count,
    SUM(o.net_sales)                AS total_revenue,
    ROUND(AVG(o.net_sales), 2)      AS avg_order_value
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name, c.customer_segment, c.region
ORDER BY total_revenue DESC
LIMIT 10;

-- ----------------------------------------------------------------------------
-- Q2: Top 10 products by revenue
-- ----------------------------------------------------------------------------
-- Product-level revenue only exists at the order_items grain, not on orders.
SELECT
    p.product_id,
    p.product_name,
    p.product_category,
    SUM(oi.quantity)    AS units_sold,
    SUM(oi.net_sales)   AS total_revenue
FROM products p
JOIN order_items oi ON oi.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.product_category
ORDER BY total_revenue DESC
LIMIT 10;

-- ----------------------------------------------------------------------------
-- Q3: Monthly revenue trend
-- ----------------------------------------------------------------------------
SELECT
    date_trunc('month', order_date)::date AS month,
    COUNT(*)          AS order_count,
    SUM(net_sales)    AS total_revenue
FROM orders
GROUP BY 1
ORDER BY 1;

-- ----------------------------------------------------------------------------
-- Q4: Yearly revenue + YoY growth
-- ----------------------------------------------------------------------------
WITH yearly AS (
    SELECT
        EXTRACT(YEAR FROM order_date)::int AS year,
        SUM(net_sales)                     AS total_revenue
    FROM orders
    GROUP BY 1
)
SELECT
    year,
    total_revenue,
    ROUND(
        100.0 * (total_revenue - LAG(total_revenue) OVER (ORDER BY year))
        / NULLIF(LAG(total_revenue) OVER (ORDER BY year), 0),
        2
    ) AS yoy_growth_pct
FROM yearly
ORDER BY year;

-- ----------------------------------------------------------------------------
-- Q5: Revenue & margin by product category
-- ----------------------------------------------------------------------------
SELECT
    p.product_category,
    SUM(oi.net_sales)  AS total_revenue,
    SUM(oi.profit)     AS total_profit,
    ROUND(100.0 * SUM(oi.profit) / NULLIF(SUM(oi.net_sales), 0), 2) AS margin_pct
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.product_category
ORDER BY total_revenue DESC;

-- ----------------------------------------------------------------------------
-- Q6: Revenue & fulfillment by region
-- ----------------------------------------------------------------------------
-- Uses orders' own `region` column (denormalized at order time) directly,
-- with no join to customers: the order-time value is the correct one for a
-- historical report, and joining would also collide with the customers
-- table's own `region` column.
-- NOTE: delivery_status = 'Cancelled' is this dataset's catch-all for "did
-- not complete a normal on-time delivery" — it bundles true cancellations,
-- still-pending orders, AND returns together (every returned order also
-- shows delivery_status = 'Cancelled'). It is NOT a narrow "cancelled only"
-- flag, so on_time/delayed % is the meaningful fulfillment signal here, not
-- "1 - cancelled %".
SELECT
    region,
    COUNT(*)                                                                    AS order_count,
    SUM(net_sales)                                                              AS total_revenue,
    ROUND(100.0 * COUNT(*) FILTER (WHERE delivery_status = 'On Time') / COUNT(*), 2)   AS on_time_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE delivery_status = 'Delayed')  / COUNT(*), 2)   AS delayed_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE delivery_status = 'Early')    / COUNT(*), 2)   AS early_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE delivery_status = 'Cancelled')/ COUNT(*), 2)   AS cancelled_pending_or_returned_pct
FROM orders
GROUP BY region
ORDER BY total_revenue DESC;

-- ----------------------------------------------------------------------------
-- Q7: Average order value by sales channel
-- ----------------------------------------------------------------------------
SELECT
    sales_channel,
    COUNT(*)                    AS order_count,
    ROUND(AVG(net_sales), 2)    AS avg_order_value,
    SUM(net_sales)              AS total_revenue
FROM orders
GROUP BY sales_channel
ORDER BY total_revenue DESC;

-- ----------------------------------------------------------------------------
-- Q8: Return rate — overall, and by product category
-- ----------------------------------------------------------------------------
-- Overall
SELECT
    COUNT(*) FILTER (WHERE return_status IS NOT NULL) AS returned_orders,
    COUNT(*)                                            AS total_orders,
    ROUND(100.0 * COUNT(*) FILTER (WHERE return_status IS NOT NULL) / COUNT(*), 2) AS return_rate_pct
FROM orders;

-- By category — one order can contain items from multiple categories, so
-- this counts distinct (order, category) pairs: an order that touched a
-- category counts once for that category regardless of item count.
SELECT
    p.product_category,
    COUNT(DISTINCT oi.order_id)                                                     AS orders_with_category,
    COUNT(DISTINCT oi.order_id) FILTER (WHERE o.return_status IS NOT NULL)          AS returned_orders,
    ROUND(
        100.0 * COUNT(DISTINCT oi.order_id) FILTER (WHERE o.return_status IS NOT NULL)
        / COUNT(DISTINCT oi.order_id),
        2
    ) AS return_rate_pct
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
JOIN orders   o ON o.order_id   = oi.order_id
GROUP BY p.product_category
ORDER BY return_rate_pct DESC;

-- ----------------------------------------------------------------------------
-- Q9: Rating distribution & its relationship to returns/delivery
-- ----------------------------------------------------------------------------
-- Rating distribution
SELECT rating, COUNT(*) AS num_ratings
FROM ratings
GROUP BY rating
ORDER BY rating;

-- "Correlation with returns" is structurally degenerate in this dataset:
-- return_status is only ever set when delivery_status = 'Cancelled', which
-- is exactly the state that also blocks a rating from ever being collected
-- (the same structural-nulls pattern the schema comments describe). So no
-- returned order can ever
-- carry a rating — verify that disjointness explicitly rather than compute
-- a misleading Pearson correlation on an all-null slice.
SELECT
    COUNT(*) FILTER (WHERE o.return_status IS NOT NULL)                          AS returned_orders_total,
    COUNT(*) FILTER (WHERE o.return_status IS NOT NULL AND r.rating IS NOT NULL) AS returned_orders_with_a_rating
FROM orders o
LEFT JOIN ratings r ON r.order_id = o.order_id;

-- The real, non-degenerate correlate within rated (i.e. delivered) orders is
-- delivery timeliness, matching the EDA's -0.16 rating/delivery_days finding.
SELECT
    o.delivery_status,
    COUNT(r.rating)             AS num_ratings,
    ROUND(AVG(r.rating), 2)     AS avg_rating
FROM orders o
JOIN ratings r ON r.order_id = o.order_id
GROUP BY o.delivery_status
ORDER BY avg_rating DESC;

-- ----------------------------------------------------------------------------
-- Q10: Profitability vs. discount level
-- ----------------------------------------------------------------------------
SELECT
    CASE
        WHEN discount_amount = 0 THEN '0% (no discount)'
        WHEN discount_amount / NULLIF(gross_sales, 0) <= 0.10 THEN '1-10%'
        WHEN discount_amount / NULLIF(gross_sales, 0) <= 0.20 THEN '11-20%'
        WHEN discount_amount / NULLIF(gross_sales, 0) <= 0.30 THEN '21-30%'
        ELSE '30%+'
    END AS discount_band,
    COUNT(*)                            AS order_count,
    ROUND(AVG(profit_margin_percentage), 2) AS avg_margin_pct,
    SUM(net_sales)                      AS total_revenue,
    SUM(profit)                         AS total_profit
FROM orders
GROUP BY 1
ORDER BY 1;

-- ----------------------------------------------------------------------------
-- Q11: Marketing-channel ROI
-- ----------------------------------------------------------------------------
-- This dataset has no per-campaign ad-spend figure, only a one-time
-- `customer_acquisition_cost` per customer. Proxy for ROI: attribute each
-- customer's acquisition cost once, to the channel of their *first* order
-- (their acquisition touchpoint), then measure total lifetime revenue that
-- customer generated per acquisition dollar spent through that channel.
WITH first_order AS (
    SELECT DISTINCT ON (customer_id) customer_id, marketing_channel
    FROM orders
    WHERE marketing_channel IS NOT NULL
    ORDER BY customer_id, order_date ASC
),
customer_revenue AS (
    -- Pre-aggregate to one row per customer first, so joining it to
    -- `customers` (also one row per customer) below can't fan out and
    -- double-count acquisition cost or revenue across a customer's orders.
    SELECT customer_id, SUM(net_sales) AS lifetime_revenue
    FROM orders
    GROUP BY customer_id
)
SELECT
    fo.marketing_channel,
    COUNT(DISTINCT fo.customer_id)                          AS customers_acquired,
    SUM(cr.lifetime_revenue)                                AS lifetime_revenue,
    ROUND(SUM(c.customer_acquisition_cost), 2)              AS total_acquisition_cost,
    ROUND(
        SUM(cr.lifetime_revenue) / NULLIF(SUM(c.customer_acquisition_cost), 0),
        2
    ) AS revenue_per_acquisition_dollar
FROM first_order fo
JOIN customer_revenue cr ON cr.customer_id = fo.customer_id
JOIN customers c         ON c.customer_id  = fo.customer_id
GROUP BY fo.marketing_channel
ORDER BY lifetime_revenue DESC;
