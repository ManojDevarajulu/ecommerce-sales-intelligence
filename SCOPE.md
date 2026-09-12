# Project Scope — E-Commerce Sales Intelligence Platform

**Status: LOCKED baseline (v1).** This is the single source of truth for what
gets built. Any change to it must be proposed, discussed, and logged in
[INTERVIEW_PREP.md](INTERVIEW_PREP.md) before it's acted on — see
[RULES.md](RULES.md) rule 4. For the atomic, task-by-task build checklist,
see [TASKS.md](TASKS.md) — that file, not this one, is what gets worked
through step by step.

Assignment: `Manoj_D_2-Day_Assessment.pdf`. Deadline: **14 Sept, before 11 AM**.

## Scope philosophy
Core-evaluation tasks (ML, OpenRouter reports, RAG) get real engineering rigor.
CRUD/tests/Docker/docs are done properly but plainly — no gold-plating. The
one "interesting addition" stays small and cheap, reusing work already done
elsewhere — it is not a second frontend product.

## Known facts (carried over from earlier exploration — verify again once rebuilt)
- Dataset lives in `data/dataset/`: `customer_master.csv` (25,000 customers),
  `product_catalog.csv` (1,175 products), `ecommerce_sales_customer_analytics_150k.csv`
  (138,116 orders, order-grain, 46 columns), `order_items.csv` (397,569 line
  items), `dataset_statistics.csv` (published ground-truth totals).
- **"Total Revenue" / "Average Order Value" are defined on `net_sales`
  (post-discount), not `gross_sales`** — confirmed by matching
  `dataset_statistics.csv` exactly ($177,134,263.74 / $1,282.50). Using
  `gross_sales` overstates both by ~7%.
- `order_status = 'Returned'` and `return_status IS NOT NULL` agree exactly
  (9,462 orders, 6.85%) — redundant fields, not conflicting ones.
- `delivery_days`, `customer_rating`, `review_sentiment`, `customer_review`
  are null together for the same ~17.8% of orders — those orders were never
  delivered (cancelled/pending), so nothing to rate.
- 89 of the 25,000 master customers never placed an order (24,911 appear in
  orders — matches the dataset's published "Total Customers").
- `dataset_statistics.csv`'s "Total Products Used" column is a mislabeled
  duplicate of "Total Transactions" (both 138,116) — not a real product
  count. Worth one line in the EDA as a data-quality callout, not a silent
  workaround.
- **Local environment**: this machine runs a native Postgres on port 5432
  already — map the Docker Postgres container to host port **5435** instead.
  A Docker named volume persists old credentials across `down`/`up`; use
  `down -v` whenever DB credentials change.

## Phases

1. **Scaffold & environment** — project structure, `requirements.txt`,
   `Dockerfile`, `docker-compose.yml` (Postgres via `pgvector/pgvector:pg16`,
   host port 5435), `.env.example`, git init.
2. **Task 1 — EDA** — one notebook (`notebooks/eda.ipynb`; no separate
   duplicate script — the PDF asks for the notebook *or* an equivalent
   module, not both). Record counts/dtypes/missingness/duplicates, date
   parsing, outlier checks, core metrics (using `net_sales`, per above),
   breakdowns by category/region/channel/time, top 10 products & customers,
   5+ business insights.
3. **Task 2 — Postgres schema + data load** — `customers`, `products`,
   `orders` (order-level totals + customer-state-at-order-time fields, to
   avoid ML leakage), `order_items`, and a **separate `ratings` table**
   (split out from orders — matches the PDF's suggested entity list). PKs/
   FKs/checks/indexes, documented ER diagram. Bulk loader via `COPY`, ending
   in a reconciliation check against `dataset_statistics.csv`. 11 SQL
   analytics queries covering every PDF-required category.
4. **Tasks 3 & 4 — FastAPI CRUD + Analytics APIs** — full CRUD on
   customers/products/orders (Pydantic validation, pagination, filtering/
   sorting, correct status codes — including a 409 when a delete is blocked
   by a foreign key). Six analytics endpoints wrapping the SQL queries, with
   date/region/category filters.
5. **Tasks 5 & 6 — ML model + prediction API** — Problem: **Order Return
   Prediction** (classification). Time-based split (train 2021–24, test
   2025). Feature engineering: discount ratio, shipping ratio, delivery
   delay, customer historical signals. Two models: Logistic Regression
   baseline vs. HistGradientBoostingClassifier. Metrics: Precision/Recall/F1/
   ROC-AUC **and PR-AUC** (return rate is only 6.85%, so ROC-AUC alone would
   be misleading) + confusion matrix. `POST /ml/predict` returns probability
   + a lightweight rule-based "contributing factors" list (not SHAP — not
   worth the dependency/time here).
6. **Task 7 — OpenRouter business reports** — deterministic SQL/Python for
   all numbers; LLM only for narrative synthesis. Reports: orders,
   customer-ratings, customer-segments (RFM). Deterministic fallback for
   offline dev — but a real OpenRouter call must actually be exercised and
   the model name documented before submission (explicitly graded).
7. **Task 8 — RAG assistant** — knowledge-base markdown docs (reusing EDA/
   analytics findings, not new analysis) → chunking → local
   `sentence-transformers` embeddings → pgvector storage/search → OpenRouter
   generation → similarity-threshold hallucination guard ("insufficient
   data" response) → source citations in the response.
8. **Delighters (max 3, cheap, reuse existing work)**:
   - RAG chat widget — one static HTML page (free Bootstrap/Tabler-style
     template via CDN), hits `/ai/rag/query`, shows answer + citations.
     Served by FastAPI at `/`.
   - ML model card (`ml/MODEL_CARD.md`) — auto-generated from training
     metadata.
   - Saved eval plots (confusion matrix, ROC/PR curve) as PNGs from
     `train.py`.
   - *Explicitly out of scope*: KPI-card dashboards, live Chart.js
     visualizations, an ML probability gauge, a one-click multi-report UI —
     Swagger already covers "interactive," and a second frontend product is
     not in scope.
9. **Tests** — 5–10 tests: CRUD success/validation/404, analytics endpoint,
   ML prediction endpoint, RAG/AI report endpoint.
10. **Docs** — README covering every PDF-required section (overview,
    architecture diagram, ER diagram, setup, env vars, API examples, EDA
    findings, ML approach, LLM report architecture, RAG architecture,
    assumptions/limitations, future improvements, AI-assistance disclosure).

## Change log
*(Append here whenever scope changes after this baseline — date, what
changed, why, who/what approved it.)*

- 2026-09-12 — v1 baseline locked.
