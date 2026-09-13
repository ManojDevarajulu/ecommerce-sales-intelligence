# Rating Analysis — Customer Ratings, Review Sentiment and What Drives Them

Source: PostgreSQL `ratings` table (113,559 rated orders) joined to `orders`, `customers` and `order_items`, 2021–2025. A rating exists only for orders that completed a normal delivery; the 24,557 returned, cancelled and pending orders (17.78% of all orders) have no rating by construction. Ratings are on a 1.0–5.0 scale with one decimal place. Every number here comes from a SQL query, not an estimate.

## Rating headline numbers

- **113,559 rated orders** (82.2% of all 138,116 orders).
- **Average rating: 3.68 / 5**; median 3.7; the most common rating is 3.7 (9,362 orders).
- Ratings span **1.6 to 5.0**.
- **28.95% of ratings are 4.0 or higher**; only **0.05% (56 orders) are 2.0 or lower**; 386 orders (0.34%) gave a perfect 5.0.
- The average rating is identical in every year: 2021 3.67, 2022–2025 3.68 — no upward or downward trend over five years.
- The catalog's static `product_rating` field also averages 3.68 (range 2.5–4.9), matching customer order ratings.

## Rating distribution — the major pattern

Ratings form a tight, bell-shaped distribution centred just below 4:

| Rating band | Orders | Share |
|-------------|--------|-------|
| 1.6 – 2.4 (poor) | 792 | 0.70% |
| 2.5 – 2.9 | 7,090 | 6.24% |
| 3.0 – 3.4 | 27,594 | 24.30% |
| 3.5 – 3.9 (most common band) | 45,209 | 39.81% |
| 4.0 – 4.4 | 27,035 | 23.81% |
| 4.5 – 5.0 (excellent) | 5,839 | 5.14% |

Individual values in the peak: 3.5 → 8,755 (7.71%), 3.6 → 9,085 (8.00%), 3.7 → 9,362 (8.24%), 3.8 → 9,263 (8.16%), 3.9 → 8,744 (7.70%), 4.0 → 7,718 (6.80%).

Patterns:

- **Ratings cluster in a narrow "satisfied but not delighted" band**: 64% of all ratings fall between 3.5 and 4.4. There are very few strongly negative experiences (under 1% below 2.5) and relatively few enthusiastic ones (5% at 4.5+).
- **The distribution is extremely stable** — the same average (3.68) every year, in every region (3.67–3.68), every sales channel (3.67–3.68), every shipping method (3.67–3.68) and every product category (3.67–3.70). Almost nothing about *what* was bought or *where* changes the rating.
- What *does* move ratings is **delivery speed** and **customer segment** (see the sections below).

## Review sentiment

Each rated order also carries a review sentiment label:

| Sentiment | Orders | Share | Avg rating |
|-----------|--------|-------|------------|
| Positive | 78,083 | 68.76% | 3.93 |
| Neutral | 34,684 | 30.54% | 3.14 |
| Negative | 792 | 0.70% | 2.28 |

**Sentiment is overwhelmingly positive (68.8%) or neutral (30.5%); only 0.7% of reviews are negative.** The three sentiment groups map cleanly onto rating levels (Positive ≈ 3.9, Neutral ≈ 3.1, Negative ≈ 2.3), so sentiment and numeric rating are consistent with each other. Negative reviews (792) match exactly the number of ratings below 2.5.

## Delivery timeliness is the strongest driver of ratings

Average rating by delivery outcome:

| Delivery status | Rated orders | Avg rating | Avg delivery days |
|-----------------|--------------|------------|-------------------|
| Early | 9,757 | **4.02** | 2.93 |
| On Time | 86,916 | 3.73 | 4.30 |
| Delayed | 16,886 | **3.22** | 6.83 |

Average rating by actual delivery time:

| Delivery time | Rated orders | Avg rating |
|---------------|--------------|------------|
| 0–2 days | 28,919 | 3.76 |
| 3–5 days | 41,972 | 3.69 |
| 6–8 days | 31,857 | 3.64 |
| 9+ days | 10,811 | 3.50 |

- **Early deliveries are rated 0.80 points higher than delayed ones (4.02 vs 3.22)** — by far the largest gap of any factor in the dataset. On-time orders sit at 3.73.
- Rating falls steadily as delivery takes longer: 3.76 for orders arriving within 2 days, down to 3.50 for 9+ days. The EDA found a −0.16 correlation between delivery days and rating; these bands show the same relationship.
- Delayed orders are 14.9% of delivered orders (16,886), so eliminating delays would lift the overall average rating meaningfully — if delayed orders were rated like on-time ones (3.73 instead of 3.22), the company average would rise from 3.68 to about 3.76.
- Shipping method itself does not change the rating (Express 3.68, Same Day 3.68, Standard 3.68, Economy 3.67) — what matters is whether the order beat, met, or missed its promised date, not which service was chosen.

## Ratings by customer segment

| Customer segment | Rated orders | Avg rating |
|------------------|--------------|------------|
| VIP | 11,506 | **3.83** |
| Premium | 28,544 | 3.73 |
| Business | 11,298 | 3.63 |
| Consumer | 62,211 | 3.63 |

VIP customers rate 0.20 points higher than Consumer and Business customers (3.83 vs 3.63); Premium sits between (3.73). This is the second-largest rating gap in the data after delivery timeliness, and the only place where the pre-assigned segment labels show a real behavioural difference.

## Ratings by product category

| Category | Rated orders | Avg rating |
|----------|--------------|------------|
| Electronics | 19,899 | 3.70 |
| Toys & Games | 19,981 | 3.70 |
| Sports & Outdoors | 22,816 | 3.70 |
| Jewelry | 17,734 | 3.70 |
| Automotive | 20,561 | 3.69 |
| Baby & Kids | 19,375 | 3.69 |
| Books & Media | 21,899 | 3.69 |
| Fashion | 17,562 | 3.69 |
| Home & Kitchen | 17,860 | 3.69 |
| Office Supplies | 20,415 | 3.69 |
| Health & Wellness | 21,766 | 3.68 |
| Beauty & Personal Care | 21,139 | 3.68 |
| Pet Supplies | 18,897 | 3.68 |
| Home Appliances | 19,918 | 3.68 |
| Grocery | 19,966 | 3.67 |

Category has essentially no effect on ratings: the full range is 3.67 (Grocery) to 3.70 (Electronics, Toys & Games, Sports & Outdoors, Jewelry) — a 0.03 spread. Product satisfaction is uniform; the rating is about the *experience* (delivery), not the product line.

## Ratings by sales channel and region

- Sales channel: Mobile App 3.68 (45,505 ratings), Social Media 3.68 (11,461), Website 3.68 (39,606), Marketplace 3.67 (16,987).
- Region: Central 3.68, South 3.68, East 3.67, North 3.67, West 3.67.

Neither channel nor region moves the average by more than 0.01.

## Ratings and returns — why they cannot be correlated here

**No returned order has a rating.** All 9,462 returned orders carry `delivery_status = 'Cancelled'` (the dataset's umbrella status for any order that did not complete a normal delivery), which is exactly the state in which no rating is collected — verified directly: 0 of 9,462 returned orders have a rating. Ratings therefore cannot be used to predict or explain returns in this dataset, and the ML return-prediction model deliberately excludes rating and review fields for this reason. Return-rate patterns live in the product and regional analyses instead (highest: Automotive 7.21%; lowest: Baby & Kids 6.59%).

## Summary — the major patterns in customer ratings

1. Average rating is **3.68 / 5** and has been flat for five years; ratings cluster tightly between 3.5 and 4.4 (64%), with under 1% strongly negative.
2. **Sentiment is 68.8% positive, 30.5% neutral, 0.7% negative.**
3. **Delivery timeliness is the dominant driver**: early 4.02 → on time 3.73 → delayed 3.22; every extra delivery-day band lowers the rating (3.76 at 0–2 days to 3.50 at 9+ days).
4. **VIP customers rate higher** (3.83) than Consumer/Business customers (3.63).
5. Product category, region, sales channel and shipping method make **no practical difference** (spreads of 0.01–0.03).
6. Ratings exist only for delivered orders, so they cannot be linked to returns.

Recommendation: the single most effective lever for raising ratings is reducing the 14.9% of deliveries that arrive late — not product changes, regional changes or channel changes.
