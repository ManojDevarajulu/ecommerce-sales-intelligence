# Business Metrics — Company-Wide KPIs (2021–2025)

Source: the loaded PostgreSQL `orders` table (138,116 orders, 2021-01-01 to 2025-12-31), reconciled to the cent against the dataset's published `dataset_statistics.csv`. All revenue figures are **net sales** (after discounts) unless stated otherwise. Every number in this document was produced by a SQL query against the database, not estimated.

## Headline KPIs (all time, 2021–2025)

- Total orders (transactions): **138,116**
- Total customers who placed at least one order: **24,911** (out of 25,000 registered customers; 89 never ordered)
- Total revenue (net sales): **$177,134,263.74**
- Gross sales before discounts: **$189,962,560.88** — gross overstates revenue by $12,828,297.14 (+7.24%), so "revenue" always means net sales
- Total discounts given: **$32,819,346.82** (17.28% of gross sales)
- Total profit: **$76,146,395.76**, an overall profit margin of **42.99%** of net sales
- Average order value (AOV): **$1,282.50** (net sales per order)
- Total units sold (order-level quantity): **775,555**
- Overall return rate: **6.85%** (9,462 returned orders)
- Overall cancellation rate: **6.08%** (8,398 cancelled orders)
- Average customer rating: **3.68 / 5** across 113,559 rated orders

## Revenue by year and year-over-year growth

Revenue is remarkably flat across the five years — the business is neither growing nor shrinking materially. Order volume sits at roughly 27.5–27.8k orders every year.

| Year | Orders | Revenue (net) | Profit | YoY revenue growth |
|------|--------|---------------|--------|--------------------|
| 2021 | 27,554 | $35,722,650.67 | $15,325,651.87 | — |
| 2022 | 27,564 | $35,327,882.62 | $15,167,978.69 | −1.11% |
| 2023 | 27,632 | $35,528,143.74 | $15,247,695.95 | +0.57% |
| 2024 | 27,768 | $35,466,452.28 | $15,292,965.09 | −0.17% |
| 2025 | 27,598 | $35,089,134.43 | $15,112,104.16 | −1.06% |

2021 was the best year ($35.72M) and 2025 the weakest ($35.09M), a total decline of only 1.8% over five years. Profit tracks revenue almost exactly (margin ~43% every year).

## Seasonality — monthly revenue pattern

Revenue has a strong, repeating Q4 peak. Summing all five years by calendar month:

| Month | Orders | Revenue (net) | AOV |
|-------|--------|---------------|-----|
| January | 9,693 | $12,238,598.83 | $1,262.62 |
| February | 8,027 | $10,108,027.56 | $1,259.25 |
| March | 10,822 | $13,679,516.86 | $1,264.05 |
| April | 10,120 | $12,654,092.89 | $1,250.40 |
| May | 10,238 | $12,626,730.13 | $1,233.32 |
| June | 10,880 | $13,470,903.94 | $1,238.13 |
| July | 10,207 | $14,054,324.07 | $1,376.93 |
| August | 12,064 | $15,058,347.23 | $1,248.21 |
| September | 10,855 | $13,814,730.98 | $1,272.66 |
| October | 11,582 | $14,606,076.52 | $1,261.10 |
| November | 16,061 | $21,524,457.18 | $1,340.17 |
| December | 17,567 | $23,298,457.55 | $1,326.26 |

- **November + December together produce $44.82M, 25.3% of all revenue, from 24.3% of all orders** — the holiday season is the single most important trading period.
- **December is the top-revenue month in every one of the five years** (best single month: December 2021, $4,900,970.07 from 3,568 orders). **February is the weakest month in every year** (worst: February 2021, $1,905,413.15 from 1,565 orders). A December month brings in roughly 2.1–2.6× a February month of the same year.
- July has the highest AOV of any month ($1,376.93) despite average order volume, and November/December also carry an above-average AOV ($1,340 / $1,326) — customers spend more per order in the peak season, not just more often.
- August is a secondary mid-year bump (12,064 orders, $15.06M).

## Order status breakdown

| Order status | Orders | Share | Revenue (net) |
|--------------|--------|-------|---------------|
| Completed | 113,559 | 82.22% | $144,195,838.50 |
| Returned | 9,462 | 6.85% | $13,172,674.79 |
| Cancelled | 8,398 | 6.08% | $11,356,479.77 |
| Pending | 6,697 | 4.85% | $8,409,270.68 |

82.2% of orders complete normally. The remaining 24,557 orders (17.78%) — returned, cancelled, or pending — all carry `delivery_status = 'Cancelled'` and have no delivery time or customer rating, because none of them finished a normal delivery lifecycle. Returns are the largest of the three non-completed states and represent $13.17M of order value.

## Delivery performance (all orders)

| Delivery status | Orders | Share of all orders | Avg delivery days |
|-----------------|--------|---------------------|-------------------|
| On Time | 86,916 | 62.93% | 4.30 |
| Delayed | 16,886 | 12.23% | 6.83 |
| Early | 9,757 | 7.06% | 2.93 |
| Cancelled (umbrella for returned / cancelled / pending) | 24,557 | 17.78% | n/a |

Among the 113,559 orders that were actually delivered: **76.5% arrived on time, 14.9% were delayed, and 8.6% arrived early**. Delayed orders take on average 6.83 days versus 4.30 for on-time and 2.93 for early deliveries. The "Cancelled" delivery status is a catch-all for any order that did not complete a normal delivery — it includes every returned order — so it must not be read as "the customer cancelled".

## Shipping methods

| Shipping method | Orders | Share | Avg delivery days | Avg shipping cost |
|-----------------|--------|-------|-------------------|-------------------|
| Standard | 62,006 | 44.89% | 5.25 | $18.71 |
| Express | 34,373 | 24.89% | 2.26 | $27.62 |
| Economy | 27,824 | 20.15% | 7.74 | $16.44 |
| Same Day | 13,913 | 10.07% | 0.82 | $36.65 |

Standard shipping is the default choice for ~45% of orders. Same Day costs about double Standard ($36.65 vs $18.71) and is used on 10% of orders; Economy is the slowest at 7.74 days on average.

## Payment methods

| Payment method | Orders | Share | Revenue (net) | AOV |
|----------------|--------|-------|---------------|-----|
| Credit Card | 41,460 | 30.02% | $53,389,617.40 | $1,287.74 |
| Debit Card | 27,635 | 20.01% | $35,355,144.13 | $1,279.36 |
| PayPal | 20,750 | 15.02% | $26,632,143.06 | $1,283.48 |
| Digital Wallet | 16,382 | 11.86% | $20,832,787.20 | $1,271.69 |
| Cash on Delivery | 13,863 | 10.04% | $18,025,912.13 | $1,300.29 |
| Buy Now Pay Later | 11,061 | 8.01% | $13,974,727.03 | $1,263.42 |
| Bank Transfer | 6,965 | 5.04% | $8,923,932.79 | $1,281.25 |

Cards (credit + debit) account for half of all orders. AOV is nearly identical across payment methods ($1,263–$1,300); Cash on Delivery has the highest AOV at $1,300.29 and Buy Now Pay Later the lowest at $1,263.42.

## Sales channels

| Sales channel | Orders | Share | Revenue (net) | AOV |
|---------------|--------|-------|---------------|-----|
| Mobile App | 55,318 | 40.05% | $70,834,782.53 | $1,280.50 |
| Website | 48,237 | 34.92% | $61,854,736.08 | $1,282.31 |
| Marketplace | 20,698 | 14.99% | $26,696,190.22 | $1,289.80 |
| Social Media | 13,863 | 10.04% | $17,748,554.91 | $1,280.28 |

The Mobile App is the largest sales channel (40% of orders, $70.8M), followed by the Website (35%). Together the two owned digital channels generate 75% of revenue. AOV is flat across channels (~$1,280–$1,290), so channel mix affects volume, not basket size.

## Return rate trend by year

| Year | Returned orders | Total orders | Return rate |
|------|-----------------|--------------|-------------|
| 2021 | 1,825 | 27,554 | 6.62% |
| 2022 | 1,825 | 27,564 | 6.62% |
| 2023 | 1,888 | 27,632 | 6.83% |
| 2024 | 1,952 | 27,768 | 7.03% |
| 2025 | 1,972 | 27,598 | 7.15% |

The return rate has crept up every year since 2022, from 6.62% to 7.15% in 2025 (+0.53 percentage points). This is a small but consistent upward trend worth monitoring; the all-time average is 6.85%.

## Definitions and data notes

- **Revenue = net sales** (post-discount order total). Gross sales ($189.96M) is pre-discount and is not the revenue figure. This definition is what makes the totals match the dataset's published statistics exactly.
- **AOV** = average of `net_sales` per order = $1,282.50.
- **Profit margin** = total profit / total net sales = 42.99%.
- **Return rate** = orders with `order_status = 'Returned'` / all orders = 6.85%. `return_status IS NOT NULL` gives the identical 9,462 orders.
- **Cancellation rate** = orders with `order_status = 'Cancelled'` / all orders = 6.08%.
- **Order-level vs item-level revenue**: the `order_items` line-item table sums to $192,398,877.29, which is 8.6% higher than the order-level total of $177,134,263.74 (11,226 orders, 8.1%, have line items that sum above their order total — a source-data inconsistency). Company-level KPIs use the order-level total; product and category revenue can only be computed from line items and therefore use the $192.40M item-level base. Both are stated explicitly wherever they appear.
- **Delivery status "Cancelled"** is an umbrella state for returned, cancelled, and pending orders (24,557 orders, 17.78%), not only customer cancellations.
