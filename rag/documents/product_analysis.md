# Product Analysis — Categories, Products, Brands, Margins and Returns

Source: PostgreSQL `products` (1,175 products) and `order_items` (397,569 line items across 138,116 orders), 2021–2025. Product- and category-level revenue can only be computed at the line-item grain, whose total is **$192,398,877.29** — 8.6% above the order-level company revenue of $177,134,263.74 (a known source-data inconsistency). Category revenue shares below are shares of the $192.40M item-level total. Every number here comes from a SQL query, not an estimate.

## Product catalog overview

- **1,175 products** across **15 categories**, 117 sub-categories, **144 brands**, and 10 suppliers.
- Unit prices range from **$6.31 to $1,482.95**; the average list price is $245.52.
- Every one of the 1,175 catalog products was sold at least once (1,175 distinct products appear in order items).
- Average line items per order: 2.88 (397,569 items / 138,116 orders); total units sold at line-item grain: 842,366.
- Catalog `product_rating` (a static per-product score) averages 3.68, ranging 2.5–4.9 — coincidentally the same average as the customer order ratings (3.68).

Products per category (catalog counts, largest first): Sports & Outdoors 91, Books & Media 87, Health & Wellness 86, Beauty & Personal Care 83, Automotive 81, Office Supplies 80, Electronics 78, Home Appliances 78, Grocery 78, Toys & Games 77, Baby & Kids 75, Pet Supplies 74, Home & Kitchen 70, Jewelry 69, Fashion 68. The catalog is evenly spread — no category has more than 7.7% of SKUs.

## Revenue and profit margin by product category

Ranked by line-item net revenue (share is of the $192.40M item-level total):

| Rank | Category | Revenue (net) | Share | Profit | Margin |
|------|----------|---------------|-------|--------|--------|
| 1 | Electronics | $41,148,162.90 | 21.39% | $14,103,982.74 | 34.28% |
| 2 | Jewelry | $25,561,333.78 | 13.29% | $10,391,635.32 | 40.65% |
| 3 | Home Appliances | $24,842,478.64 | 12.91% | $10,288,878.45 | 41.42% |
| 4 | Automotive | $16,449,898.28 | 8.55% | $6,477,194.28 | 39.38% |
| 5 | Sports & Outdoors | $15,726,848.17 | 8.17% | $7,230,037.31 | 45.97% |
| 6 | Home & Kitchen | $10,971,629.82 | 5.70% | $5,203,824.25 | 47.43% |
| 7 | Baby & Kids | $9,690,605.60 | 5.04% | $4,818,148.07 | 49.72% |
| 8 | Health & Wellness | $9,228,068.04 | 4.80% | $4,263,304.41 | 46.20% |
| 9 | Office Supplies | $8,884,212.85 | 4.62% | $4,585,377.04 | 51.61% |
| 10 | Fashion | $7,434,589.51 | 3.86% | $3,669,631.60 | 49.36% |
| 11 | Pet Supplies | $6,421,229.71 | 3.34% | $3,263,681.62 | 50.83% |
| 12 | Toys & Games | $5,472,675.99 | 2.84% | $2,800,442.39 | 51.17% |
| 13 | Beauty & Personal Care | $4,735,647.66 | 2.46% | $2,477,469.89 | 52.32% |
| 14 | Grocery | $2,990,696.44 | 1.55% | $1,648,934.90 | 55.14% |
| 15 | Books & Media | $2,840,799.90 | 1.48% | $1,475,496.28 | 51.94% |

Key findings:

- **Electronics is the dominant category**: $41.15M, 21.4% of item-level revenue — 1.6× the next category. **The top three categories (Electronics, Jewelry, Home Appliances) together generate $91.55M, 47.6% of item-level revenue.**
- **Revenue and margin are inversely related.** Electronics, the biggest revenue category, has the **lowest margin (34.28%)**; Grocery, the second-smallest revenue category, has the **highest margin (55.14%)**. High-ticket categories (Electronics, Automotive, Jewelry, Home Appliances) all sit at 34–41% margin; low-ticket categories (Grocery, Beauty, Books, Toys, Office, Pet) all sit at 51–55%.
- **Books & Media is the smallest revenue category ($2.84M, 1.48%)** despite having the second-largest catalog (87 products) and the second-highest order count (26,758 orders touch it) — its average unit price is only $45.32.
- Order counts per category are surprisingly even (21,255–27,700 orders each): customers buy across all categories at similar frequency; the revenue differences come almost entirely from price points, not popularity.

## Average price point by category

| Category | Products | Avg unit price | Price range |
|----------|----------|----------------|-------------|
| Electronics | 78 | $798.84 | $207.18 – $1,482.95 |
| Jewelry | 69 | $566.81 | $99.24 – $971.74 |
| Home Appliances | 78 | $479.14 | $107.95 – $793.35 |
| Automotive | 81 | $304.74 | $39.50 – $590.78 |
| Sports & Outdoors | 91 | $261.44 | $39.79 – $498.63 |
| Home & Kitchen | 70 | $236.69 | $19.23 – $398.04 |
| Baby & Kids | 75 | $191.86 | $19.05 – $347.09 |
| Office Supplies | 80 | $164.24 | $19.77 – $299.68 |
| Fashion | 68 | $162.29 | $32.72 – $299.92 |
| Health & Wellness | 86 | $158.63 | $17.18 – $291.89 |
| Pet Supplies | 74 | $128.71 | $10.03 – $249.48 |
| Toys & Games | 77 | $102.75 | $17.04 – $196.29 |
| Beauty & Personal Care | 83 | $82.44 | $11.83 – $148.59 |
| Grocery | 78 | $54.19 | $6.31 – $97.82 |
| Books & Media | 87 | $45.32 | $10.53 – $79.96 |

Electronics products average $798.84 — 17.6× the average Books & Media price ($45.32). The category revenue ranking above follows this price ranking almost exactly.

## Top 10 products by revenue

All ten of the highest-revenue products are Electronics (gaming consoles, TVs, tablets, smart watches, smartphones, cameras). Revenue is line-item net sales.

| Rank | Product ID | Product | Sub-category | Brand | Units | Revenue |
|------|------------|---------|--------------|-------|-------|---------|
| 1 | PROD-000065 | Xiaomi Self-enabling exuding productivity | Gaming Consoles | Xiaomi | 743 | $956,726.44 |
| 2 | PROD-000062 | OnePlus Adaptive uniform success | Gaming Consoles | OnePlus | 767 | $946,819.10 |
| 3 | PROD-000074 | Asus Configurable upward-trending matrix | TVs | Asus | 778 | $943,941.34 |
| 4 | PROD-000024 | Asus Re-engineered content-based strategy | Tablets | Asus | 673 | $942,549.52 |
| 5 | PROD-000051 | HP Versatile actuating budgetary management | Smart Watches | HP | 717 | $909,388.15 |
| 6 | PROD-000077 | OnePlus Switchable methodical neural-net | TVs | OnePlus | 716 | $900,378.69 |
| 7 | PROD-000043 | OnePlus Streamlined modular infrastructure | Smart Watches | OnePlus | 754 | $885,456.49 |
| 8 | PROD-000012 | LG Reverse-engineered even-keeled workforce | Smartphones | LG | 668 | $883,013.59 |
| 9 | PROD-000063 | Xiaomi Fundamental motivating task-force | Gaming Consoles | Xiaomi | 738 | $857,409.58 |
| 10 | PROD-000056 | HP Function-based neutral access | Cameras | HP | 711 | $853,769.80 |

The best-selling product by revenue is PROD-000065 (Xiaomi gaming console) at $956,726.44. Each of the top 10 sells roughly 670–780 units over five years and brings in $0.85M–$0.96M; no single product exceeds 0.5% of item-level revenue, so revenue is not concentrated in a handful of SKUs.

## Top products by units sold

By volume the picture is different — cheap, frequently bought items lead:

| Rank | Product ID | Product | Category | Units | Revenue |
|------|------------|---------|----------|-------|---------|
| 1 | PROD-000839 | Arm & Hammer Organized maximized software (Grooming) | Pet Supplies | 904 | $135,755.74 |
| 2 | PROD-000003 | LG Face-to-face client-driven support (Smartphones) | Electronics | 865 | $223,670.71 |
| 3 | PROD-000694 | Goodyear Managed clear-thinking secured line (Tools) | Automotive | 854 | $369,900.26 |
| 4 | PROD-000449 | Adidas Public-key homogeneous functionalities (Team Sports) | Sports & Outdoors | 846 | $295,343.54 |
| 5 | PROD-000549 | HarperCollins Operative multi-tasking budgetary management (Movies) | Books & Media | 844 | $15,579.38 |

The most-sold single product is a Pet Supplies grooming item (904 units). The HarperCollins movie title sells 844 units yet earns only $15,579 — a clear illustration that unit volume and revenue rank very differently.

## Top brands by revenue

| Rank | Brand | Revenue (net, item-level) | Units |
|------|-------|---------------------------|-------|
| 1 | Samsung | $6,922,013.66 | 11,402 |
| 2 | LG | $6,165,232.04 | 11,652 |
| 3 | OnePlus | $5,080,134.21 | 6,540 |
| 4 | Asus | $4,831,788.72 | 4,985 |
| 5 | HP | $4,550,295.21 | 7,071 |

The five top brands are all electronics brands; Samsung leads at $6.92M. Even the largest brand is only 3.6% of item-level revenue — the 144-brand catalog is highly fragmented.

## Return rate by product category

Return rate = distinct orders containing the category that were returned / distinct orders containing the category (an order containing several categories counts once for each). Overall company return rate is 6.85%.

| Rank | Category | Orders with category | Returned | Return rate |
|------|----------|----------------------|----------|-------------|
| 1 | Automotive | 25,103 | 1,811 | **7.21%** |
| 2 | Jewelry | 21,578 | 1,520 | 7.04% |
| 3 | Health & Wellness | 26,468 | 1,859 | 7.02% |
| 4 | Home & Kitchen | 21,744 | 1,517 | 6.98% |
| 5 | Electronics | 24,235 | 1,684 | 6.95% |
| 6 | Sports & Outdoors | 27,700 | 1,921 | 6.94% |
| 7 | Home Appliances | 24,241 | 1,673 | 6.90% |
| 8 | Grocery | 24,177 | 1,662 | 6.87% |
| 9 | Pet Supplies | 23,020 | 1,576 | 6.85% |
| 10 | Books & Media | 26,758 | 1,830 | 6.84% |
| 11 | Office Supplies | 24,908 | 1,694 | 6.80% |
| 12 | Beauty & Personal Care | 25,656 | 1,724 | 6.72% |
| 13 | Fashion | 21,255 | 1,421 | 6.69% |
| 14 | Toys & Games | 24,245 | 1,604 | 6.62% |
| 15 | Baby & Kids | 23,389 | 1,542 | **6.59%** |

- **Automotive has the highest return rate at 7.21%**, followed by Jewelry (7.04%) and Health & Wellness (7.02%).
- **Baby & Kids has the lowest return rate at 6.59%**, followed by Toys & Games (6.62%) and Fashion (6.69%).
- The spread between the highest and lowest category is only **0.62 percentage points** (7.21% vs 6.59%). Category matters, but return behaviour is broadly uniform across the catalog — no category is a dramatic outlier. In absolute terms Sports & Outdoors has the most returned orders (1,921) simply because it appears in the most orders.

## Return reasons (all categories)

Of the 9,462 returned orders, reasons are spread almost evenly across eight causes:

| Return reason | Orders | Share of returns |
|---------------|--------|------------------|
| Wrong Product | 1,237 | 13.07% |
| Other | 1,208 | 12.77% |
| Changed Mind | 1,204 | 12.72% |
| Size Issue | 1,182 | 12.49% |
| Defective Product | 1,174 | 12.41% |
| Late Delivery | 1,172 | 12.39% |
| Product Not as Expected | 1,147 | 12.12% |
| Damaged Product | 1,138 | 12.03% |

"Wrong Product" is the single most common reason (13.07%). Grouping them: fulfilment/operations issues (Wrong Product, Late Delivery, Damaged Product) account for 37.5% of returns; product quality/description issues (Defective, Not as Expected, Size Issue) for 37.0%; customer-side (Changed Mind) for 12.7%.

## Recommendations grounded in the product data

- **Protect Electronics volume, but manage its margin**: it is 21% of revenue at the lowest margin (34%). Bundling Electronics with high-margin accessories (Office Supplies 52%, Beauty 52%) lifts blended margin without sacrificing the traffic driver.
- **Promote high-margin, low-share categories** (Grocery 55%, Beauty & Personal Care 52%, Books & Media 52%, Toys & Games 51%) as basket add-ons: each extra dollar there earns roughly 1.5× the profit of an Electronics dollar.
- **Target Automotive, Jewelry and Health & Wellness for return-reduction** (the three highest return rates, 7.02–7.21%), starting with "Wrong Product" and "Size Issue" fixes — better listings, sizing/fitment guides and pick accuracy.
- Because the top 10 products are all Electronics and none exceeds 0.5% of revenue, stock-outs of any single SKU are low risk; category-level availability matters more than individual hero products.
