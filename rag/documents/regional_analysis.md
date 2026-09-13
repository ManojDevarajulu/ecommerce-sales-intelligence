# Regional Analysis — Revenue, Profitability, Fulfilment and Returns by Region

Source: PostgreSQL `orders` (138,116 orders, 2021–2025), using the `region` recorded on each order, joined to `customers`/`order_items` where noted. Revenue is net sales (post-discount), order-level, total $177,134,263.74. The business operates five regions — South, Central, West, East, North — which are cross-country sales territories grouping states from 7 countries (USA, UK, Germany, Canada, Australia, India, UAE), not subdivisions of one country. Every number here comes from a SQL query, not an estimate.

## Revenue and order volume by region

| Rank | Region | Orders | Order share | Revenue (net) | Revenue share | AOV | Customers |
|------|--------|--------|-------------|---------------|---------------|-----|-----------|
| 1 | South | 43,990 | 31.85% | $55,587,994.98 | 31.38% | $1,263.65 | 7,964 |
| 2 | Central | 29,627 | 21.45% | $37,171,107.17 | 20.98% | $1,254.64 | 5,345 |
| 3 | West | 26,273 | 19.02% | $34,755,096.47 | 19.62% | $1,322.84 | 4,731 |
| 4 | East | 21,602 | 15.64% | $27,054,887.88 | 15.27% | $1,252.43 | 3,860 |
| 5 | North | 16,624 | 12.04% | $22,565,177.24 | 12.74% | $1,357.39 | 3,011 |

- **South is the largest region by every volume measure**: 31.4% of revenue ($55.59M), 31.9% of orders and 7,964 customers — about 1.5× the size of Central, the second-largest.
- **North is the smallest region (12.7% of revenue, $22.57M) but has the highest average order value at $1,357.39**, 7.4% above the South's $1,263.65 and 5.8% above the company AOV of $1,282.50. West is second on AOV ($1,322.84).
- Revenue share tracks customer share closely (South has 32.0% of registered customers and 31.4% of revenue), so regional revenue differences are driven by customer count, with North and West earning slightly more per order.

## Profitability by region

| Region | Revenue (net) | Profit | Profit margin |
|--------|---------------|--------|---------------|
| South | $55,587,994.98 | $23,343,946.17 | 41.99% |
| Central | $37,171,107.17 | $15,572,868.84 | 41.90% |
| West | $34,755,096.47 | $15,647,252.47 | 45.02% |
| East | $27,054,887.88 | $11,179,366.94 | 41.32% |
| North | $22,565,177.24 | $10,402,961.34 | 46.10% |

**North (46.10%) and West (45.02%) are the most profitable regions per dollar of revenue**; South, Central and East all sit at 41.3–42.0%. The company-wide margin is 42.99%. The two high-AOV regions are also the two high-margin regions, so a North or West order is worth more in both revenue and profit than a South, Central or East order. West in fact earns more total profit ($15.65M) than Central ($15.57M) despite $2.4M less revenue.

## Which regions are performing strongly?

Three different answers depending on the measure:

- **By size**: South — largest revenue ($55.59M, 31.4%), most orders and most customers.
- **By quality of revenue**: North — highest AOV ($1,357.39) and highest margin (46.10%); West — second on both (AOV $1,322.84, margin 45.02%) and the only region whose revenue grew over the period (see the trend section).
- **By customer satisfaction and returns**: East — lowest return rate (6.40%) and highest on-time delivery share (63.33%), though also the lowest AOV ($1,252.43) and lowest margin (41.32%).

Central is the weakest on quality measures: second-lowest AOV ($1,254.64, essentially tied with East's $1,252.43), a margin of 41.90%, the lowest on-time delivery share (62.48%), and the joint-highest return rate (7.11%).

## Regional revenue trend, 2021–2025

| Region | 2021 | 2022 | 2023 | 2024 | 2025 | Change 2021→2025 |
|--------|------|------|------|------|------|------------------|
| South | $11,260,839.14 | $11,152,847.75 | $11,058,692.18 | $11,087,098.99 | $11,028,516.92 | −2.1% |
| Central | $7,582,255.54 | $7,282,237.96 | $7,510,831.19 | $7,461,780.04 | $7,334,002.44 | −3.3% |
| West | $6,832,955.26 | $6,917,417.12 | $6,988,547.29 | $6,918,748.60 | $7,097,428.20 | **+3.9%** |
| East | $5,466,687.16 | $5,352,087.23 | $5,564,473.50 | $5,488,816.19 | $5,182,823.80 | −5.2% |
| North | $4,579,913.57 | $4,623,292.56 | $4,405,599.58 | $4,510,008.46 | $4,446,363.07 | −2.9% |

Regional revenue is flat to slightly declining, mirroring the company-wide picture (−1.8% over five years). **West is the only region that grew between 2021 and 2025 (+3.9%)**, and 2025 was its best year. **East declined the most (−5.2%)**, with 2025 its worst year. South declined in three of the four year-on-year steps (only 2024 ticked up) but remains far larger than any other region.

## Fulfilment and delivery performance by region

Delivery status shares are of all orders in the region. "Cancelled" is the dataset's umbrella status for returned + cancelled + pending orders (none of which completed a normal delivery), not customer cancellations alone.

| Region | On Time | Delayed | Early | Cancelled (umbrella) | Avg delivery days (delivered orders) |
|--------|---------|---------|-------|----------------------|--------------------------------------|
| South | 62.84% | 12.28% | 7.18% | 17.70% | 4.55 |
| Central | 62.48% | 12.30% | 7.10% | 18.12% | 4.59 |
| West | 63.18% | 12.04% | 7.07% | 17.71% | 4.53 |
| East | 63.33% | 12.31% | 6.95% | 17.41% | 4.56 |
| North | 63.06% | 12.12% | 6.83% | 17.99% | 4.57 |

Fulfilment is uniform across regions: on-time share is 62.5–63.3% everywhere, delayed share 12.0–12.3%, and average delivery time 4.53–4.59 days. No region has a logistics problem relative to the others. East has the best on-time rate (63.33%) and the smallest non-completed share (17.41%); Central has the lowest on-time rate (62.48%) and the largest non-completed share (18.12%).

Orders are also spread evenly across 19 warehouses (WH-001 to WH-019), each handling 5.2–5.4% of orders with average delivery times of 4.47–4.66 days and delayed rates of 11.65–12.89%. No warehouse is an outlier.

## Return rate by region

| Region | Return rate | Company average |
|--------|-------------|-----------------|
| Central | 7.11% | 6.85% |
| North | 7.11% | 6.85% |
| West | 6.92% | 6.85% |
| South | 6.76% | 6.85% |
| East | 6.40% | 6.85% |

**Central and North have the highest return rates (7.11% each); East has the lowest (6.40%).** The spread is 0.71 percentage points — wider than the spread across product categories (0.62 pp), so region is a marginally stronger return signal than category, but still small.

## Customer ratings by region

Average customer rating (1–5) on delivered orders: Central 3.68 (24,259 ratings), South 3.68 (36,205), East 3.67 (17,841), North 3.67 (13,633), West 3.67 (21,621). Ratings are flat across regions — within 0.01 of the company average of 3.68 — so satisfaction is not a regional issue.

## Top product categories within each region

Electronics is the #1 revenue category in every region, followed by Jewelry and Home Appliances in every region (line-item revenue):

| Region | #1 | #2 | #3 |
|--------|----|----|----|
| South | Electronics $12,947,251.84 | Jewelry $8,169,516.95 | Home Appliances $7,792,106.01 |
| Central | Electronics $8,663,619.19 | Home Appliances $5,259,920.58 | Jewelry $5,204,571.03 |
| West | Electronics $8,052,976.06 | Jewelry $5,027,133.91 | Home Appliances $4,774,186.36 |
| East | Electronics $6,284,155.39 | Jewelry $3,941,503.19 | Home Appliances $3,783,188.26 |
| North | Electronics $5,200,160.42 | Home Appliances $3,233,077.43 | Jewelry $3,218,608.70 |

Category mix does not vary by region — the same three categories lead everywhere, in nearly the same order (Central and North have Home Appliances narrowly ahead of Jewelry). Regional strategy therefore does not need region-specific assortments.

## Geography behind the regions

Customers come from 7 countries: USA 14,925 (59.7% of the base), UK 3,701, Germany 2,046, Canada 1,279, Australia 1,233, India 1,041, UAE 775 — across 38 states/provinces and 15,555 cities. Each business region mixes states from several countries (for example, "East" contains New York, Pennsylvania, Ontario, Quebec and New South Wales; "West" contains California, British Columbia, Wales, Gujarat and Western Australia).

Top states by revenue (all US): Pennsylvania (East) $11,291,298.72 from 9,148 orders; California (West) $10,638,192.45; New York (East) $10,458,664.29; Georgia (South) $10,397,100.94; Ohio (Central) $10,212,975.30; Michigan (Central) $10,092,885.95; Texas (South) $9,999,313.06; Illinois (Central) $9,859,476.12; North Carolina (South) $9,706,101.58; Florida (South) $9,574,082.95. The ten US states are remarkably even ($9.6M–$11.3M each), and the South's lead comes from having four of the top ten states.

## Recommendations grounded in the regional data

- **Grow North and West**: they are the smallest regions by volume but the most profitable per order (46.1% / 45.0% margin, AOV $1,357 / $1,323). Profit per order is $625.79 in North and $595.56 in West versus $551.32 company-wide — 8–14% more profit per order. West is also the only region already growing (+3.9%).
- **Investigate East's decline (−5.2% since 2021)** — it has the best delivery and lowest return rate, so the drop is not an operations problem; it is a demand/customer-count issue (East has only 3,860 active customers).
- **Reduce returns in Central and North (7.11%)** toward East's 6.40%; at Central's volume (29,627 orders), matching East's rate would avoid roughly 210 returns.
- Do not regionalise the assortment or logistics — category mix, delivery times and ratings are uniform across all five regions.
