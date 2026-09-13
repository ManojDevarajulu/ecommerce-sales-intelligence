# Customer Analysis — Base, Segments, Behaviour and RFM Targeting

Source: PostgreSQL `customers` (25,000 registered customers) joined to `orders` (138,116 orders, 2021–2025). Revenue is net sales (post-discount), order-level, total $177,134,263.74. The RFM segmentation is computed by the platform's own `compute_rfm_and_segments()` service, with recency measured from the dataset's last order date (2025-12-31). Every number here comes from a SQL query or that service, not an estimate.

## Customer base overview

- **25,000 registered customers**, of whom **24,911 (99.6%) placed at least one order**; 89 never ordered.
- Ages range from 18 to 74, average age **45.9**.
- Gender: Female 12,048 (48.2%), Male 11,976 (47.9%), Non-Binary 976 (3.9%).
- Average customer acquisition cost (CAC): **$42.16** per customer; total acquisition spend across the base **$1,053,993.76**.
- Customers are spread across 7 countries (USA 14,925 — 59.7%; UK 3,701; Germany 2,046; Canada 1,279; Australia 1,233; India 1,041; UAE 775) and grouped into 5 business regions: South 7,996 (32.0%), Central 5,358 (21.4%), West 4,750 (19.0%), East 3,874 (15.5%), North 3,022 (12.1%).

## Purchase frequency and customer lifetime value

Across the 24,911 active customers:

- **Average orders per customer: 5.54** (median 5; minimum 1; maximum 19).
- **Average lifetime revenue per customer: $7,110.68** (median $6,516.90; the single highest-value customer has spent $30,268.44).
- **97.9% of customers are repeat buyers**: 24,387 customers placed 2+ orders; only 524 (2.1%) placed exactly one order.
- Average order value is $1,282.50, so a typical customer's lifetime value ≈ 5.5 orders × $1,282 ≈ $7,100.
- With CAC at $42.16 and average lifetime revenue at $7,110.68, revenue per acquisition dollar is roughly **169×** — acquisition cost is negligible relative to lifetime spend, which means retention (keeping the 5.5-order pattern going) matters far more than the cost of acquiring.

## Pre-assigned customer segments (`customer_segment` column)

The dataset labels every customer as Consumer, Premium, VIP or Business. This is a business-assigned label, not a behavioural one.

| Segment | Customers | Share of base | Orders | Revenue (net) | Revenue share | AOV | Return rate |
|---------|-----------|---------------|--------|---------------|---------------|-----|-------------|
| Consumer | 13,638 | 54.55% | 75,636 | $97,201,007.90 | 54.87% | $1,285.12 | 6.84% |
| Premium | 6,301 | 25.20% | 34,746 | $44,269,794.13 | 24.99% | $1,274.10 | 6.85% |
| VIP | 2,542 | 10.17% | 13,957 | $17,903,164.81 | 10.11% | $1,282.74 | 6.69% |
| Business | 2,519 | 10.08% | 13,777 | $17,760,296.90 | 10.03% | $1,289.13 | 7.06% |

Findings: each segment's revenue share equals its share of customers almost exactly — Consumers are 54.6% of customers and 54.9% of revenue; VIPs are 10.2% of customers and 10.1% of revenue. **VIP and Premium customers do not spend more per order or order more often than Consumers** (AOV $1,274–$1,289 everywhere). The labels therefore do not identify high-value behaviour. The only behavioural differences are small: VIP has the lowest return rate (6.69%) and Business the highest (7.06%), and VIP customers give the highest ratings (3.83 average vs 3.63 for Consumer and Business).

## RFM segmentation (behaviour-based) — who to target

RFM scores each of the 24,911 active customers on Recency (days since last order, as of 2025-12-31), Frequency (order count) and Monetary (lifetime net sales), each into quintiles 1–5, then assigns a named segment. Total monetary across all segments = $177,134,263.74 (the full company revenue).

| Segment | Customers | Share of customers | Lifetime revenue | Revenue share | Avg recency (days) | Avg orders |
|---------|-----------|--------------------|------------------|---------------|--------------------|------------|
| Loyal | 6,090 | 24.4% | $53,624,321.19 | 30.3% | 280.2 | 7.43 |
| Champions | 3,874 | 15.6% | $46,014,167.17 | 26.0% | 55.8 | 8.37 |
| Needs Attention | 6,440 | 25.9% | $38,267,861.76 | 21.6% | 125.1 | 4.63 |
| At Risk | 3,284 | 13.2% | $23,468,150.55 | 13.2% | 559.5 | 4.74 |
| Lost | 4,168 | 16.7% | $12,211,267.25 | 6.9% | 703.7 | 2.94 |
| New | 1,055 | 4.2% | $3,548,495.82 | 2.0% | 62.3 | 2.69 |

Segment definitions: **Champions** = top-two quintiles on all three of R, F and M (recent, frequent, high-spending). **Loyal** = frequent buyers (F ≥ 4) who are not Champions. **At Risk** = previously frequent or high-spending customers (F ≥ 3 or M ≥ 3) who have not bought recently (R ≤ 2). **New** = only one purchase quintile (F = 1) but bought recently (R ≥ 4). **Lost** = bottom-two quintiles on all three. **Needs Attention** = everyone else (mid-range on every dimension).

Key findings:

- **Champions + Loyal are 40.0% of customers but 56.3% of lifetime revenue ($99.64M).** Champions are the most valuable per head: 3,874 customers, 8.37 orders each, last purchase 56 days ago on average, $11,878 lifetime revenue each.
- **At Risk is the highest-value rescue opportunity**: 3,284 customers who generated $23.47M (13.2% of revenue, $7,146 each) but have not ordered for 559 days on average — a year and a half.
- **Lost** customers (4,168, $12.21M) last bought 704 days ago on average and only ordered 2.94 times; they are the least likely to return and the least valuable to chase.
- **Needs Attention** is the largest segment (6,440 customers, 25.9%) with mid-range behaviour (4.63 orders, 125 days since last purchase) — the biggest pool for moving customers up into Loyal.
- **New** customers (1,055) bought recently (62 days) but only 2.69 times so far — a second-purchase nurture audience.

## Which customer segments should the business target?

Based on the RFM numbers above, in priority order:

1. **Champions (3,874 customers, $46.0M, 26% of revenue)** — retain and reward. They are the most recent buyers (56 days on average), the most frequent (8.37 orders) and the highest spenders per head ($11,878); the goal is protecting this revenue (early access, loyalty tier benefits), not discounting to them.
2. **At Risk (3,284 customers, $23.5M)** — win-back campaigns. These were high-value buyers (4.74 orders, $7,146 each) who have gone quiet for ~18 months; a targeted reactivation offer has the highest revenue-at-stake per customer of any lapsed group.
3. **Loyal (6,090 customers, $53.6M, 30% of revenue)** — the largest revenue block. They order often (7.43 times) but their last order averages 280 days ago, so the opportunity is increasing recency: replenishment reminders and cross-category recommendations to move them toward Champions.
4. **Needs Attention (6,440 customers, $38.3M)** — the biggest upgrade pool; personalised recommendations to lift frequency from 4.6 orders toward the Loyal threshold.
5. **New (1,055 customers)** — second-purchase onboarding within 60 days.
6. **Lost (4,168 customers, $12.2M)** — lowest priority; 704 days inactive with under 3 orders each. Low-cost reactivation only (email), not paid media.

The pre-assigned VIP/Premium labels should *not* be used as the targeting basis, because they show no behavioural difference from Consumers (see the segment table above).

## Top 10 customers by lifetime revenue

| Rank | Customer ID | Name | Segment | Region | Orders | Lifetime revenue | AOV |
|------|-------------|------|---------|--------|--------|------------------|-----|
| 1 | CUST-012869 | Dylan Clark | Consumer | East | 15 | $30,268.44 | $2,017.90 |
| 2 | CUST-002969 | Tracy Mendez | Premium | West | 16 | $30,061.58 | $1,878.85 |
| 3 | CUST-017251 | Jesus Ross | Premium | South | 15 | $29,375.34 | $1,958.36 |
| 4 | CUST-000802 | Rodney Avila | Consumer | West | 12 | $28,503.23 | $2,375.27 |
| 5 | CUST-012608 | James Long | Premium | South | 13 | $28,172.12 | $2,167.09 |
| 6 | CUST-017828 | Joyce Cooper | Business | South | 14 | $28,092.99 | $2,006.64 |
| 7 | CUST-006857 | Hailey Cox | Consumer | Central | 10 | $26,835.08 | $2,683.51 |
| 8 | CUST-017523 | Ryan Stewart | Consumer | North | 9 | $26,776.65 | $2,975.18 |
| 9 | CUST-008822 | Patrick Hunter | Premium | East | 10 | $25,803.66 | $2,580.37 |
| 10 | CUST-001747 | Kristie Lucas | Consumer | North | 15 | $25,737.14 | $1,715.81 |

The top customer, Dylan Clark, has spent $30,268.44 over 15 orders. Notably, 5 of the top 10 are labelled "Consumer", 4 "Premium" and 1 "Business" — none is a "VIP" — further evidence that the pre-assigned segment labels do not track actual spend. Top customers spend $1,700–$3,000 per order versus the $1,282.50 company AOV, and revenue is not concentrated: the #1 customer is only 0.017% of total revenue.

## Demographics — age and gender

Revenue by age band (active customers):

| Age band | Customers | Orders | Revenue (net) | AOV |
|----------|-----------|--------|---------------|-----|
| 18–24 | 3,039 | 16,961 | $21,741,941.07 | $1,281.88 |
| 25–34 | 4,399 | 24,537 | $31,373,178.11 | $1,278.61 |
| 35–44 | 4,429 | 24,542 | $31,653,669.74 | $1,289.78 |
| 45–54 | 4,347 | 23,849 | $30,478,086.09 | $1,277.96 |
| 55–64 | 4,367 | 24,213 | $30,992,833.25 | $1,280.01 |
| 65+ | 4,330 | 24,014 | $30,894,555.48 | $1,286.52 |

Revenue by gender: Female $85,215,914.19 (66,439 orders, AOV $1,282.62), Male $84,900,594.89 (66,284 orders, AOV $1,280.86), Non-Binary $7,017,754.66 (5,393 orders, AOV $1,301.27).

Spending is essentially uniform across ages and genders: every 10-year band from 25 upward contributes $30.5–31.7M, and AOV sits within $1,278–$1,301 for every demographic group. The 18–24 band is smaller only because it spans 7 years rather than 10. Demographics do not identify high-value customers in this data; purchase behaviour (RFM) does.

## Loyalty programme usage

- Loyalty points earned across all orders: **14,362,828**; points redeemed: **7,172,934** (49.9% of earned points are redeemed).
- **80.34% of orders (110,961) redeem at least some loyalty points** — the programme is heavily used, so it is a realistic channel for the retention actions recommended above.

## Data notes

- The orders table also carries a `customer_type` field (Loyal 129,447 orders — 93.72%; Returning 8,335 — 6.03%; New 334 — 0.24%). Only 334 orders are labelled "New" even though all 24,911 customers necessarily had a first order, so this field is a pre-assigned label and **not** a reliable first-purchase indicator. The RFM "New" segment above is behaviour-derived and should be used instead.
- Lifetime revenue and RFM use order-level net sales, so segment revenues sum exactly to the company total of $177,134,263.74.
