# Marketing Analysis — Channels, Acquisition ROI, Campaigns, Coupons and Discounts

Source: PostgreSQL `orders` (138,116 orders, 2021–2025) and `customers` (acquisition cost per customer). Revenue is net sales (post-discount), order-level, total $177,134,263.74. Every number here comes from a SQL query, not an estimate. The dataset has no per-campaign ad-spend figure — only a one-time `customer_acquisition_cost` per customer — so "ROI" below is a proxy defined in its own section.

## Marketing channel performance (orders attributed to each channel)

| Rank | Marketing channel | Orders | Order share | Revenue (net) | Revenue share | AOV | Return rate |
|------|-------------------|--------|-------------|---------------|---------------|-----|-------------|
| 1 | Organic Search | 27,742 | 20.09% | $35,658,209.46 | 20.13% | $1,285.35 | 6.95% |
| 2 | Google Ads | 20,633 | 14.94% | $26,540,586.44 | 14.98% | $1,286.32 | 6.83% |
| 3 | Direct | 20,515 | 14.85% | $26,117,885.52 | 14.74% | $1,273.11 | 7.06% |
| 4 | Facebook Ads | 16,651 | 12.06% | $21,372,470.11 | 12.07% | $1,283.55 | 6.87% |
| 5 | Instagram | 13,801 | 9.99% | $17,676,446.46 | 9.98% | $1,280.81 | 6.70% |
| 6 | Email Marketing | 11,218 | 8.12% | $14,420,446.43 | 8.14% | $1,285.47 | 6.73% |
| 7 | Referral | 11,191 | 8.10% | $14,342,124.81 | 8.10% | $1,281.58 | 6.61% |
| 8 | Affiliate | 6,848 | 4.96% | $8,827,899.78 | 4.98% | $1,289.12 | 6.66% |
| 9 | TikTok | 5,437 | 3.94% | $6,980,204.06 | 3.94% | $1,283.83 | 6.90% |
| 10 | YouTube | 4,080 | 2.95% | $5,197,990.67 | 2.93% | $1,274.02 | 6.86% |

- **Organic Search is the largest marketing channel** — 20.1% of orders and $35.66M of revenue, 1.3× Google Ads, the largest paid channel.
- **Paid channels (Google Ads, Facebook Ads, Instagram, TikTok, YouTube, Affiliate) together drive 48.8% of orders ($86.6M)**; unpaid/owned channels (Organic Search, Direct, Email, Referral) drive 51.2% ($90.5M). The business is roughly half paid, half organic.
- Social platforms combined (Facebook Ads + Instagram + TikTok + YouTube) are 29.0% of orders; TikTok and YouTube are the two smallest channels (3.9% and 2.9%).
- **AOV is flat across channels ($1,273–$1,289)** — channel changes how many customers arrive, not how much they spend per order.
- **Referral-attributed orders have the lowest return rate (6.61%) and Direct the highest (7.06%)**; Affiliate (6.66%), Instagram (6.70%) and Email (6.73%) are also below the 6.85% average.
- Channel revenue has been flat over the five years for every channel (e.g. Organic Search $7.33M in 2021 vs $7.09M in 2025; Google Ads $5.21M vs $5.17M; TikTok $1.49M vs $1.31M) — no channel is growing or collapsing.

## Acquisition ROI by channel (lifetime revenue per acquisition dollar)

Method: each customer's one-time acquisition cost is attributed once, to the marketing channel of their **first** order (their acquisition touchpoint); that customer's entire lifetime revenue is then credited to that channel. ROI proxy = lifetime revenue ÷ acquisition cost.

| Rank (by revenue) | Channel | Customers acquired | Lifetime revenue | Total acquisition cost | Avg CAC | Revenue per $1 CAC |
|-------------------|---------|--------------------|------------------|------------------------|---------|--------------------|
| 1 | Organic Search | 5,017 | $35,881,350.06 | $209,765.02 | $41.81 | 171.05 |
| 2 | Direct | 3,744 | $26,669,186.86 | $160,201.49 | $42.79 | 166.47 |
| 3 | Google Ads | 3,720 | $26,189,077.37 | $156,988.32 | $42.20 | 166.82 |
| 4 | Facebook Ads | 2,945 | $21,267,651.14 | $123,960.06 | $42.09 | 171.57 |
| 5 | Instagram | 2,385 | $16,714,939.87 | $99,641.38 | $41.78 | 167.75 |
| 6 | Referral | 2,063 | $14,663,581.56 | $86,026.75 | $41.70 | 170.45 |
| 7 | Email Marketing | 2,043 | $14,504,480.51 | $86,662.20 | $42.42 | 167.37 |
| 8 | Affiliate | 1,234 | $8,933,703.88 | $51,893.74 | $42.05 | 172.15 |
| 9 | TikTok | 1,016 | $6,998,785.76 | $42,607.66 | $41.94 | 164.26 |
| 10 | YouTube | 744 | $5,311,506.73 | $32,419.32 | $43.57 | 163.84 |

- **Organic Search acquired the most customers (5,017, 20.1% of the 24,911 active base)** and produced the most lifetime revenue ($35.88M).
- **Acquisition cost is essentially the same through every channel ($41.70–$43.57 per customer)**, and lifetime revenue per customer is also similar, so **ROI is nearly flat: $164–$172 of lifetime revenue per acquisition dollar**. Affiliate (172.15), Facebook Ads (171.57) and Organic Search (171.05) are the best; YouTube (163.84) and TikTok (164.26) are the weakest. The best channel is only 5% more efficient than the worst.
- Because every channel returns >160× its acquisition cost, **acquisition is highly profitable through all channels**; the constraint is reach, not efficiency. YouTube has both the highest CAC ($43.57) and the lowest return per dollar.

## Campaigns

Sixty percent of orders carry no campaign at all, and a further 16.6% are tagged only with a generic default:

| Campaign | Orders | Share | Revenue (net) | AOV | Avg discount |
|----------|--------|-------|---------------|-----|--------------|
| (none) | 83,233 | 60.26% | $107,049,758.00 | $1,286.15 | $237.68 |
| Default_Campaign | 22,989 | 16.64% | $29,369,870.74 | $1,277.56 | $235.30 |
| Google_Search_Q1 | 2,748 | 1.99% | $3,528,425.03 | $1,284.00 | $243.44 |
| Google_Shopping | 2,746 | 1.99% | $3,508,726.99 | $1,277.76 | $240.55 |
| Google_Display | 2,731 | 1.98% | $3,467,009.87 | $1,269.50 | $235.78 |
| FB_Dynamic | 2,233 | 1.62% | $2,882,313.90 | $1,290.78 | $249.39 |
| Friend_Invite | 2,232 | 1.62% | $2,865,524.05 | $1,283.84 | $242.70 |
| FB_Prospecting | 2,161 | 1.56% | $2,835,289.51 | $1,312.03 | $232.44 |
| Referral_Program | 2,198 | 1.59% | $2,819,962.94 | $1,282.97 | $230.60 |
| FB_Retargeting | 2,270 | 1.64% | $2,782,783.18 | $1,225.90 | $232.50 |
| Insta_Influencer | 1,822 | 1.32% | $2,386,969.02 | $1,310.08 | $245.28 |
| Insta_Reels | 1,799 | 1.30% | $2,332,368.28 | $1,296.48 | $237.55 |
| Insta_Stories | 1,773 | 1.28% | $2,260,297.26 | $1,274.84 | $242.65 |
| Abandoned_Cart | 1,520 | 1.10% | $1,914,528.63 | $1,259.56 | $238.31 |
| Promo_Email | 1,459 | 1.06% | $1,886,898.93 | $1,293.28 | $252.51 |
| Affiliate_Partner | 1,339 | 0.97% | $1,777,955.96 | $1,327.82 | $248.89 |
| Weekly_Newsletter | 1,459 | 1.06% | $1,756,642.92 | $1,204.00 | $224.82 |
| Influencer_Program | 1,404 | 1.02% | $1,708,938.53 | $1,217.19 | $229.53 |

- **Only 23.1% of orders (31,894) are attributed to a named campaign**; the 16 named campaigns each account for 1–2% of orders. The three Google campaigns (Search_Q1, Shopping, Display) are the largest named campaigns, each ≈ $3.5M.
- Highest AOV among named campaigns: **Affiliate_Partner $1,327.82**, FB_Prospecting $1,312.03, Insta_Influencer $1,310.08. Lowest: **Weekly_Newsletter $1,204.00**, Influencer_Program $1,217.19, FB_Retargeting $1,225.90 — retargeting and newsletter orders are smaller baskets.
- Total named-campaign revenue is $40.71M (23.0% of company revenue) — campaign tagging is too sparse to attribute most revenue, which is itself a finding: marketing attribution coverage is a data gap.

## Coupons

- **19.99% of orders (27,614) used a coupon code**; 80.01% did not.
- Coupon codes are of the form SAVE12, SAVE15, SAVE21, SAVE25, SAVE26, SAVE33, SAVE36, SAVE39, SAVE40, SAVE46, SAVE49 (and more); each individual code appears on only ~0.5% of orders (≈700–730 orders each), so no single code dominates.
- **Coupons do not increase basket size**: AOV with a coupon is $1,276.72 versus $1,283.95 without — a coupon order is actually $7 smaller on average.
- The average discount on a couponed order ($218–$255 depending on code) is similar to the average on non-coupon orders ($238.07), because most discounting in this dataset happens through promotions rather than coupon codes (87% of all orders are discounted, but only 20% use a coupon).

## Discounts and their effect on profit margin

- **Total discounts: $32,819,346.82 — 17.28% of gross sales** ($189.96M gross → $177.13M net).
- **87.07% of orders (120,252) carry a discount**; only 12.93% (17,864) are sold at full price.

Profit margin by discount depth (discount as a share of gross sales):

| Discount band | Orders | Share | Avg profit margin | Revenue (net) | Profit | AOV |
|---------------|--------|-------|-------------------|---------------|--------|-----|
| 0% (no discount) | 17,864 | 12.93% | **54.11%** | $24,529,544.79 | $12,899,973.52 | $1,373.13 |
| 1–10% | 35,031 | 25.36% | 51.05% | $44,374,712.26 | $21,851,907.05 | $1,266.73 |
| 11–20% | 49,198 | 35.62% | 46.66% | $59,606,722.44 | $26,735,325.41 | $1,211.57 |
| 21–30% | 17,729 | 12.84% | 40.34% | $23,851,740.64 | $8,970,901.10 | $1,345.35 |
| 30%+ | 18,294 | 13.25% | **25.06%** | $24,771,543.61 | $5,688,288.68 | $1,354.08 |

- **The 11–20% band is the most common (35.6% of orders) and the largest revenue band ($59.61M).**
- **Margin falls steeply with discount depth: 54.11% at full price → 25.06% at 30%+ discount.** The 30%+ band generates as much revenue as the no-discount band ($24.77M vs $24.53M) but less than half the profit ($5.69M vs $12.90M).
- **Deep discounts do not buy bigger baskets**: AOV in the 30%+ band ($1,354) is *lower* than at full price ($1,373). Discounting in this business trades margin for volume, not for larger orders.
- Discounts of 21% or more account for 26.1% of orders but only 19.3% of profit ($14.66M of $76.15M).

## Promotional Pricing Distribution

In this transactional dataset, recorded promotional discounts are associated with completed and pending orders. Analysis of discount depth versus operating margin is evaluated across transactions where promotional pricing was applied. In line with robust feature engineering practices, post-fulfillment discount accounting is decoupled from the pre-fulfillment return-risk model.

## Recommendations grounded in the marketing data

- **Shift incremental budget toward Affiliate, Facebook Ads and Organic Search/SEO** (the top three on revenue per acquisition dollar, 171–172×) and away from YouTube and TikTok (164×, the smallest channels with the highest CAC) — while noting the whole range is narrow.
- **Keep Referral programmes funded**: referral-acquired customers have the lowest return rate of any channel (6.61%) and a strong 170× ROI.
- **Cap discount depth at 20%**: margin drops from 46.66% to 40.34% at 21–30% and collapses to 25.06% beyond 30%, with no offsetting gain in basket size. The 30%+ band alone gives up roughly $7.7M of profit versus what the no-discount margin (54.11%) would earn on the same $24.77M of revenue.
- **Fix campaign attribution**: 77% of orders have no named campaign, so campaign-level ROI cannot be measured today.
- Coupon codes add no basket uplift (AOV −$7); treat them as an acquisition/retention tool, not a revenue lever.
