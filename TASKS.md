# Tasks — E-Commerce Sales Intelligence Platform

Spec-driven task breakdown of [SCOPE.md](SCOPE.md). Every task is atomic —
small enough that it can be individually approved, built, and verified
before moving to the next one, per [RULES.md](RULES.md) rules 2–3. Nothing
here gets built without an explicit go-ahead for that task (or an explicitly
agreed small batch of them).

**How to use this file:**

- Check a box only once the task is actually built *and* verified (run,
  tested, or eyeballed — not just "written").
- Work top to bottom within a phase; don't skip ahead to a later phase.
- If a task turns out to need splitting further, or the approach changes
  mid-task, log it in [INTERVIEW_PREP.md](INTERVIEW_PREP.md) and note it here.
- `⚠` marks a task with a real decision or trade-off worth discussing before
  building, not just executing.

Status legend: `[ ]` not started · `[x]` done · `[~]` in progress / partial

---

## Phase 1 — Scaffold & environment

- [X] **T001** Create directory structure: `app/{api,models,schemas,services,db}`, `ml/`, `rag/documents/`, `notebooks/`, `sql/`, `tests/`
- [X] **T002** Write `requirements.txt` ⚠ (confirm package versions/choices)
- [x] **T003** Write `Dockerfile` — written
- [x] **T004** Write `docker-compose.yml` (Postgres via `pgvector/pgvector:pg16`, host port **5435**) — note: references `sql/00_extensions.sql` (Phase 3) and `.env` (T005), neither exists yet — fine, just needed before T010 actually runs
- [x] **T005** Write `.env.example`
- [x] **T006** Write `.gitignore` — verify nested data paths actually match (`data/**/*.csv`, not `data/*.csv`) — confirmed via `git status data/` showing nothing untracked
- [x] **T007** `git init`
- [x] **T008** Verify `.venv` still has all required packages — spot-checked 12 key imports against pinned versions, all match
- [x] **T009** Verify Docker Desktop is running
- [x] **T010** `docker compose up -d db`, wait for healthy status — healthy; `vector` extension confirmed active (note: created `sql/00_extensions.sql` and a real local `.env` as unlisted prerequisites — see below)
- [x] **T011** Initial commit

## Phase 2 — Task 1: EDA notebook

- [x] **T012** Load the 4 source CSVs in the notebook, print shapes
- [x] **T013** Profile each table: dtypes, missing-value counts/%, duplicate rows
- [x] **T014** Document missingness reasoning as markdown (structural nulls, not bugs)
- [x] **T015** Parse date fields; derive year/month/year-month; print date range
- [x] **T016** Outlier/suspicious-value checks (profit-margin extremes, negative delivery days, order_status vs. return_status consistency, `dataset_statistics.csv` "Total Products Used" mislabel)
- [x] **T017** Compute core metrics (revenue on `net_sales`, orders, quantity, AOV, discount, profit, margin, return rate, cancellation rate, avg rating) + cross-check vs. `dataset_statistics.csv`
- [x] **T018** Revenue by category (via `order_items` + `products` — not `orders` alone)
- [x] **T019** Revenue by region (orders' own `region` column — no merge needed)
- [x] **T020** Revenue by marketing channel
- [x] **T021** Revenue by time (monthly/yearly trend)
- [x] **T022** Plots: monthly trend, category/region/channel bar charts
- [x] **T023** Top 10 products by revenue & units
- [x] **T024** Top 10 customers by revenue
- [x] **T025** Return-rate and rating breakdown by category (feeds ML + RAG docs later)
- [x] **T026** Write 5+ business insights (markdown, referencing the real computed numbers)
- [x] **T027** Execute notebook end-to-end (headless), confirm zero errors
- [x] **T028** Commit EDA notebook

## Phase 3 — Task 2: Postgres schema + data load

- [ ] **T029** `sql/01_schema.sql` — `customers` table + indexes
- [ ] **T030** `products` table + indexes
- [ ] **T031** `orders` table (order-level totals + customer-state-at-order-time fields) + indexes ⚠ (confirm which columns move to `orders` vs. stay only on `customers`)
- [ ] **T032** `order_items` table + indexes
- [ ] **T033** `ratings` table (split from orders) + indexes
- [ ] **T034** `rag_chunks` table (pgvector column)
- [ ] **T035** Apply schema to a fresh DB, confirm no errors
- [ ] **T036** `app/db/seed.py` — customers loader (`COPY`)
- [ ] **T037** products loader
- [ ] **T038** orders loader (explicit column selection/order)
- [ ] **T039** order_items loader
- [ ] **T040** ratings loader (derived from orders, non-null rating only)
- [ ] **T041** Reconciliation check vs. `dataset_statistics.csv` (revenue, profit, AOV, return rate, avg rating)
- [ ] **T042** Run full load; verify row counts match source CSVs exactly
- [ ] **T043** Run reconciliation; confirm every metric matches
- [ ] **T044** `sql/02_analytics_queries.sql` — Q1 top customers by revenue
- [ ] **T045** Q2 top products by revenue
- [ ] **T046** Q3 monthly revenue trend
- [ ] **T047** Q4 yearly revenue + YoY growth
- [ ] **T048** Q5 revenue/margin by category
- [ ] **T049** Q6 revenue/fulfillment by region
- [ ] **T050** Q7 AOV by sales channel
- [ ] **T051** Q8 return rate (overall + by category)
- [ ] **T052** Q9 rating distribution & correlation with returns
- [ ] **T053** Q10 profitability vs. discount level
- [ ] **T054** Q11 marketing-channel ROI
- [ ] **T055** Run all 11 queries against the loaded DB; sanity-check results
- [ ] **T056** Write ER diagram (mermaid) documenting the schema
- [ ] **T057** Commit schema + loader + queries

## Phase 4 — Tasks 3 & 4: FastAPI CRUD + Analytics APIs

- [ ] **T058** SQLAlchemy model: `Customer`
- [ ] **T059** `Product`
- [ ] **T060** `Order`
- [ ] **T061** `OrderItem`
- [ ] **T062** `Rating`
- [ ] **T063** Pydantic schemas: Customer (Create/Update/Response)
- [ ] **T064** Product schemas
- [ ] **T065** Order schemas
- [ ] **T066** Shared pagination helper/schema
- [ ] **T067** Customers router — GET list (pagination + filter + sort)
- [ ] **T068** Customers — GET by id (404 handling)
- [ ] **T069** Customers — POST (validation → 201)
- [ ] **T070** Customers — PUT/PATCH
- [ ] **T071** Customers — DELETE (+ 409 on FK-restricted delete)
- [ ] **T072** Products router — GET list (filter by category/brand)
- [ ] **T073** Products — GET by id
- [ ] **T074** Products — POST
- [ ] **T075** Products — PUT/PATCH
- [ ] **T076** Products — DELETE (+ 409 handling)
- [ ] **T077** Orders router — GET list (filter by date/status/customer)
- [ ] **T078** Orders — GET by id
- [ ] **T079** Orders — POST
- [ ] **T080** Orders — PUT/PATCH
- [ ] **T081** Orders — DELETE (cascades to order_items)
- [ ] **T082** Register all routers in `main.py`
- [ ] **T083** Manual smoke test — every CRUD endpoint via Swagger
- [ ] **T084** Analytics service — reusable parametrized query executor
- [ ] **T085** `GET /analytics/sales`
- [ ] **T086** `GET /analytics/customers`
- [ ] **T087** `GET /analytics/products`
- [ ] **T088** `GET /analytics/regions`
- [ ] **T089** `GET /analytics/marketing`
- [ ] **T090** `GET /analytics/ratings`
- [ ] **T091** Manual smoke test — every analytics endpoint
- [ ] **T092** Commit CRUD + analytics APIs

## Phase 5 & 6 — Tasks 5 & 6: ML model + prediction API

- [ ] **T093** Load orders + order_items + products into pandas for modeling
- [ ] **T094** Define target: `order_status == 'Returned'`
- [ ] **T095** Time-based split (train 2021–24, test 2025) ⚠ (confirm split boundary once real date distribution is checked)
- [ ] **T096** Feature: discount ratio
- [ ] **T097** Feature: shipping ratio
- [ ] **T098** Feature: delivery delay
- [ ] **T099** Categorical encoding (sales_channel, payment_method, shipping_method, region, customer_segment)
- [ ] **T100** Customer-history features (is_repeat_customer, customer_order_count, customer_lifetime_value)
- [ ] **T101** Missing-value handling strategy (esp. undelivered-order nulls)
- [ ] **T102** Build preprocessing pipeline (scaler + encoder)
- [ ] **T103** Train baseline: Logistic Regression
- [ ] **T104** Train challenger: HistGradientBoostingClassifier
- [ ] **T105** Evaluate both: precision/recall/F1/ROC-AUC/PR-AUC/confusion matrix
- [ ] **T106** Compare & select final model, write rationale
- [ ] **T107** Save model artifact (joblib) + `metadata.json`
- [ ] **T108** *(delighter)* Save eval plots (confusion matrix, ROC/PR curve) as PNGs
- [ ] **T109** *(delighter)* Generate `ml/MODEL_CARD.md` from metadata
- [ ] **T110** `ml/predict.py` — load model, transform input, predict + probability
- [ ] **T111** Rule-based "contributing factors" heuristic (not SHAP)
- [ ] **T112** Pydantic request/response schema for `/ml/predict`
- [ ] **T113** `POST /ml/predict` route
- [ ] **T114** Manual smoke test with sample orders
- [ ] **T115** Commit ML pipeline + prediction API

## Phase 7 — Task 7: OpenRouter business reports

- [ ] **T116** OpenRouter client wrapper (httpx, env-configured key/model)
- [ ] **T117** Deterministic fallback generator (no key / network failure path)
- [ ] **T118** Deterministic stats aggregator — orders report
- [ ] **T119** Prompt template + Pydantic structured-output schema — orders report
- [ ] **T120** `POST /ai/reports/orders`
- [ ] **T121** Deterministic stats aggregator — ratings report
- [ ] **T122** Prompt + schema — ratings report
- [ ] **T123** `POST /ai/reports/customer-ratings`
- [ ] **T124** RFM computation (recency/frequency/monetary)
- [ ] **T125** Prompt + schema — segmentation report
- [ ] **T126** `POST /ai/reports/customer-segments`
- [ ] **T127** Get a real OpenRouter API key, add to local `.env` ⚠ (user action)
- [ ] **T128** Run all 3 reports against real OpenRouter; confirm non-fallback responses; note model name for README
- [ ] **T129** Commit OpenRouter reports

## Phase 8 — Task 8: RAG assistant

- [ ] **T130** `rag/documents/business_metrics.md` (from EDA numbers)
- [ ] **T131** `product_analysis.md`
- [ ] **T132** `customer_analysis.md`
- [ ] **T133** `regional_analysis.md`
- [ ] **T134** `rating_analysis.md`
- [ ] **T135** `marketing_analysis.md`
- [ ] **T136** `rag/ingest.py` — markdown chunking by headers
- [ ] **T137** Embedding generation (sentence-transformers)
- [ ] **T138** Store chunks + embeddings in `rag_chunks` (pgvector)
- [ ] **T139** Build IVFFlat index post-ingest
- [ ] **T140** `rag/retrieve.py` — similarity search + hallucination-guard threshold
- [ ] **T141** OpenRouter answer generation using retrieved context
- [ ] **T142** Source-citation formatting in the response
- [ ] **T143** `POST /ai/rag/query`
- [ ] **T144** Manual test — the 4 sample questions from the PDF
- [ ] **T145** Manual test — an out-of-scope question triggers the hallucination guard
- [ ] **T146** Commit RAG implementation

## Delighter — RAG chat widget

- [ ] **T147** Pick a free static HTML template (CDN links only, no build step)
- [ ] **T148** Wire the query box (`fetch` → `/ai/rag/query`, render answer + citations)
- [ ] **T149** Mount as FastAPI static page at `/`
- [ ] **T150** Commit delighter page

## Phase 9 — Tests

- [ ] **T151** `tests/conftest.py` — fixtures (test client, DB isolation strategy)
- [ ] **T152** CRUD test — create + validate a customer
- [ ] **T153** CRUD test — 404 on missing id
- [ ] **T154** CRUD test — delete blocked by FK → 409
- [ ] **T155** Analytics test — `/analytics/sales` response shape
- [ ] **T156** ML test — `/ml/predict` valid input + probability range
- [ ] **T157** RAG/AI test — `/ai/rag/query` returns citations; hallucination-guard case
- [ ] **T158** Run full pytest suite; fix any failures
- [ ] **T159** Commit tests

## Phase 10 — Docs

- [ ] **T160** README — overview & business objective
- [ ] **T161** README — architecture diagram
- [ ] **T162** README — ER diagram
- [ ] **T163** README — installation/setup instructions
- [ ] **T164** README — environment variables table
- [ ] **T165** README — API endpoints + example requests
- [ ] **T166** README — EDA findings summary
- [ ] **T167** README — ML approach section
- [ ] **T168** README — LLM report architecture section
- [ ] **T169** README — RAG architecture section
- [ ] **T170** README — assumptions & limitations
- [ ] **T171** README — future improvements
- [ ] **T172** README — AI assistance disclosure
- [ ] **T173** Fresh-clone smoke test: `docker compose up --build` end to end
- [ ] **T174** Final pass against the PDF's submission checklist (section 19)
- [ ] **T175** Final commit

---

**Total: 175 tasks across 10 phases + 1 delighter block.**
