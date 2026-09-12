# Interview Prep & Development Log

**Purpose:** a chronological record of every major decision, issue, and fix
made during this project — so the final timeline can be reconstructed, and
so every choice in the finished system can be explained (not just recited)
in the interview. This file is append-only in spirit: add new entries at the
bottom as things happen, don't rewrite history.

**Format per entry:** date, tag, what happened, why it matters / how it was
resolved. Tags: `[DECISION]` a choice with a real trade-off, `[ISSUE]` a bug
or unexpected failure and its fix, `[ENV]` a local-machine/tooling gotcha.

---

## 2026-09-11 — Assignment received
`[DECISION]` Reviewed `Manoj_D_2-Day_Assessment.pdf`. Deadline: 14 Sept,
before 11 AM. Identified that the PDF explicitly flags three sections as
**CORE EVALUATION**: the ML task ("real ML reasoning, not only model
training"), the OpenRouter reports ("use SQL/Python for deterministic
analytics; use the LLM for interpretation"), and the RAG task ("small,
grounded, explainable"). Everything else (CRUD, analytics API, Docker,
tests) is graded hygiene, not the differentiator. This informed the whole
prioritization strategy below.

## 2026-09-11 — Scope trims agreed
`[DECISION]` Original draft plan included a full interactive dashboard
(KPI cards, live Chart.js charts, an ML probability gauge, a one-click
report generator, a RAG chat widget) as a "showcase feature." Trimmed this
down to **one static HTML page with a RAG chat box** — the PDF's own
submission checklist has no UI requirement at all, Swagger already provides
an interactive surface for every endpoint, and a second frontend product
risked eating time that the CORE EVALUATION tasks needed more. Also dropped
a duplicate `eda_analysis.py` script (the PDF asks for the notebook *or* an
equivalent module, not both) and added a **dedicated `ratings` table**
(split out of `orders`) since the PDF's suggested entity list calls out
"ratings / reviews" explicitly and it costs almost nothing extra.

## 2026-09-11 — ML problem and delighters chosen
`[DECISION]` Picked **Order Return Prediction** (classification) as the
primary ML problem — one of the four PDF-sanctioned choices, with a
genuine class-imbalance angle (~6.85% positive rate) that justifies using
**PR-AUC alongside ROC-AUC** (ROC-AUC alone is misleadingly optimistic on
imbalanced targets — this is a concrete, defensible reason, not just "more
metrics is better"). Chose a time-based split (train 2021–24, test 2025)
specifically to avoid leakage, which the PDF explicitly asks to "consider."
Delighters chosen: RAG chat widget, an auto-generated ML model card, and
saved eval plots (confusion matrix + ROC/PR curve) — all cheap because they
reuse work another task already produced.

`[DECISION]` For the delighter's frontend: chose a static HTML page (free
Bootstrap/Tabler-style template via CDN) over Streamlit. Reasoning: no new
service/port/Docker container, no ~200MB extra dependency, and it folds
directly into the FastAPI app's existing `/` route.

## 2026-09-12 — First build attempt reverted; process rules established
`[ISSUE]` An earlier session built the scaffold, DB schema, data load, and
SQL queries, then continued into the EDA notebook across multiple steps
without stopping for approval between them — even though a "check in after
each step" cadence had been agreed. This produced working code, but left
no room for the person defending this project in an interview to actually
absorb *why* each decision was made. **Resolution:** all code, docs, and
git history were deleted (dataset CSVs and the Python venv were kept, to
avoid re-downloading/re-installing); [RULES.md](RULES.md) was written to
make the process itself binding going forward — most importantly, rule 1:
log every decision/issue *as it happens*, and rule 3: one phase at a time,
explained and approved before it starts.

## 2026-09-12 — DB reconciliation caught a real metric-definition bug
`[ISSUE]` During the (since-deleted) first build, a reconciliation check
comparing loaded DB aggregates against the dataset's own
`dataset_statistics.csv` found that computed `total_revenue` and
`avg_order_value` (from `SUM(gross_sales)` / `AVG(gross_sales)`) didn't
match the published totals — off by about 7%. **Root cause:** this
dataset defines "Total Revenue" / "Average Order Value" as **`net_sales`**
(post-discount), not `gross_sales`. **Fix:** switched every revenue/AOV
calculation to `net_sales`; re-ran the check and every metric matched
exactly (revenue, profit, AOV, return rate, avg rating). **Why this
matters for the interview:** this is the concrete payoff of building a
reconciliation step at all — it's the kind of silent-but-serious bug
("dashboard shows a plausible but wrong number") that's easy to ship
without ever noticing, precisely because the number still looks reasonable.

## 2026-09-12 — Environment gotchas (local machine)
`[ENV]` **Stale Docker volume:** recreating the `db` container with
`docker compose up -d` (without `-v`) reused a Postgres data volume
initialized by an earlier session under different credentials, causing
password-auth failures even though `.env` had the "right" password.
Postgres only applies `POSTGRES_PASSWORD` on first init of an empty data
directory — a named volume persists across `up`/`down`. **Fix:**
`docker compose down -v` before changing credentials, to guarantee a known
clean state rather than trusting an unknown prior one.

`[ENV]` **Port conflict:** this machine already runs a native PostgreSQL
service on port 5432 (a separate `postgres.exe` process, not Docker).
Docker's own port-forwarding proxy was also trying to bind 5432, and the
host-side Python client was connecting to whichever process actually held
the socket — producing confusing, inconsistent auth failures that looked
like a credentials problem but weren't. **Fix:** mapped the Docker Postgres
container to host port **5435** instead (container-internal port stays
5432, so app-to-db traffic inside the Docker network is unaffected).

`[ENV]` **Jupyter nbconvert config conflict:** headless notebook execution
(`jupyter nbconvert --execute`) failed with
`ModuleNotFoundError: jupyter_contrib_nbextensions` — a global Jupyter
config on this machine (outside the project's venv) registered a
preprocessor that isn't installed here. **Fix:** run with an isolated
`JUPYTER_CONFIG_DIR` pointed at an empty directory so the global config is
never picked up.

`[ISSUE]` **Pandas groupby KeyError on `region`:** the main orders CSV
already carries its own denormalized `region` column (copied from the
customer at order time) — merging it with the `customers` table on
`customer_id` and then grouping by `"region"` raised a `KeyError`, because
pandas suffixes the overlapping column as `region_x`/`region_y` after a
merge rather than keeping a plain `region`. **Fix:** group by the orders
table's own `region` column directly; no merge needed for that analysis.

## 2026-09-12 — `.gitignore` bug: raw data almost committed
`[ISSUE]` The original `.gitignore` had `data/*.csv`, intended to exclude
the raw Kaggle CSVs from version control. That pattern only matches files
directly inside `data/`, **not** nested ones — the actual files live in
`data/dataset/*.csv`, so all five CSVs (~85MB total) were committed in the
first real commit. **Fix:** changed the pattern to `data/**/*.csv`, ran
`git rm -r --cached data/dataset`, amended the commit (safe — nothing had
been pushed anywhere), and ran `git gc --prune=now` to actually reclaim the
disk space from the now-unreferenced blobs. **Why this matters:** a repo
that's supposed to demonstrate "clean repository structure" is graded
partly on exactly this kind of hygiene — and `git status` after adding
`.gitignore` rules is the cheap way to catch it before the first commit,
not after.

## 2026-09-12 — Docs-first restart
`[DECISION]` Before any further coding: wrote `SCOPE.md` (locked baseline
plan), `RULES.md` (binding process rules, logging first among them), and
this file, so that the next build pass happens one approved phase at a
time with a running record of why each choice was made.

## 2026-09-12 — GitHub repo configuration & initial commit (Phase 1 / T011)
`[DECISION]` Configured the remote repository as `ecommerce-sales-intelligence`
(`https://github.com/ManojDevarajulu/ecommerce-sales-intelligence.git`),
standardized on the `main` branch. Intentionally avoided company names,
"assessment", or "assignment" tags so that this codebase serves as a
production-grade portfolio showcase post-interview. Verified `.gitignore`
strictly excluded `.env`, `data/`, and `.venv/` before pushing.

## 2026-09-12 — VS Code notebook association & kernel registration
`[ENV]` **VS Code raw JSON association:** VS Code initially opened `eda.ipynb`
as raw text rather than the visual Jupyter editor (causing missing kernel
selectors and play buttons). **Fix:** added workspace `.vscode/settings.json`
with `"workbench.editorAssociations": { "*.ipynb": "jupyter-notebook" }`,
registered the local `.venv` as an explicit system kernelspec
(`ecommerce-venv`), and verified headless execution via `jupyter nbconvert`.

## 2026-09-12 — Colab-style cell-by-cell EDA architecture (Phase 2)
`[DECISION]` Structured `notebooks/eda.ipynb` into a classic, cell-by-cell
exploratory workflow using pure Pandas/NumPy operations without custom class/def
abstractions, matching standard Kaggle/Colab data science conventions. Every
metric was executed and verified:
- Total Net Revenue: **$177,134,263.74** across 138,116 transactions ($1,282.50 AOV).
- Ground-truth match: Reconciled 100% against `dataset_statistics.csv` on `net_sales`.
- Proved that `gross_sales` ($189.96M) overstates corporate revenue by **$12.83M (+7.2%)**.

`[DECISION]` **Structural Null Verification on 24,557 orders:** Verified that
100% of missing delivery days and customer ratings correspond to orders with
`delivery_status == 'Cancelled'` (Cancelled, Pending, or Returned pre-shipment).
Documented why these are structural business-state nulls that must be retained
rather than artificially imputed with mean/median values.

`[ISSUE]` **Overlapping `discount_amount` column in line-item risk merge:** both
`df_items` and `df_orders` contain a `discount_amount` column. Merging the
full line items table directly into `df_orders` suffixed the columns into
`discount_amount_x` and `discount_amount_y`, throwing a `KeyError` on downstream
risk aggregations. **Fix:** isolated order-level category assignments into an
intermediate mapping table `order_categories = df_items[['order_id', 'product_id']].merge(df_products[['product_id', 'product_category']]).drop_duplicates('order_id')`
before merging back to `df_orders`, eliminating column collisions completely.

---

## Phase 2 (EDA) — Comprehensive Interview Defense & Strategic Insights

### 1. The 5 Core Business Insights (Executive Summary)

1. **Revenue Governance (`net_sales` vs. `gross_sales`)**:
   - **Data Finding**: Total corporate revenue across 138,116 orders is **$177,134,263.74** with an Average Order Value of **$1,282.50**.
   - **Interview Defense**: This matches the published `dataset_statistics.csv` benchmark to the cent *only* when evaluated on `net_sales`. Querying `gross_sales` ($189.96M) overstates corporate revenue by **$12.83M (+7.2%)** due to promotional deductions. Always establish this financial baseline before writing SQL analytics or API endpoints.

2. **Fulfillment State Machine & Structural Nulls (24,557 Orders)**:
   - **Data Finding**: Exactly 24,557 orders (~17.8%) lack delivery duration, customer ratings, and review sentiment.
   - **Interview Defense**: Cross-table filtering proves 100% of these nulls correspond to `delivery_status == 'Cancelled'` (Cancelled, Pending, or Returned pre-delivery). They are **structural nulls**, not dirty data. Imputing with mean/median would contaminate the dataset with artificial delivery times for orders that never shipped.

3. **Class Imbalance & ML Evaluation Mandate (6.85% Return Rate)**:
   - **Data Finding**: Exactly 9,462 orders were returned (6.85% return rate).
   - **Interview Defense**: In an imbalanced binary classification problem (93.15% negative class), a naive model predicting "Not Returned" achieves 93.15% accuracy while identifying zero returns. Standard ROC-AUC is misleadingly optimistic because of the large true negative volume. Our ML model (Phase 5) must be evaluated primarily on **PR-AUC (Precision-Recall AUC)**, **Precision**, and **Recall**.

4. **Category-Level Return Risk Variance**:
   - **Data Finding**: Return rates vary significantly by product category: **Health & Wellness (7.56%)**, **Automotive (7.34%)**, and **Electronics (7.16%)** have the highest return rates, while **Beauty & Personal Care (6.30%)** and **Baby & Kids (6.49%)** have the lowest.
   - **Interview Defense**: Proves that product category is an essential categorical signal for predicting return risk. This justifies including one-hot/target-encoded category features and customer historical category preferences in feature engineering.

5. **Dataset Errata Callout (`dataset_statistics.csv`)**:
   - **Data Finding**: The published benchmark table labels a column as `Total Products Used` with value `138,116`.
   - **Interview Defense**: 138,116 is an exact duplicate of `Total Transactions`. The true unique catalog count is **1,175 products** (verified via `product_catalog.csv` and `order_items['product_id'].nunique()`). Catching and documenting dataset errata demonstrates genuine analytical rigor rather than blind acceptance of documentation.

---

### 2. Key Interview Questions & Defensible Answers

* **Q: "Why did you analyze the `orders` table first before the line items?"**
  * **A**: *"In e-commerce schema design, `orders` is the primary fact table where financial transactions and fulfillment events occur, whereas `customers` and `products` are dimension lookup tables with zero nulls. Analyzing `orders` first locks in the macro ground truth (revenue, order counts, return rates). Once top-line reconciliation is established, we drill down into `order_items` for granular category and SKU decompositions."*

* **Q: "How does this EDA directly inform your database schema in Phase 3?"**
  * **A**: *"First, knowing that 24,557 orders have null ratings justifies splitting `ratings / reviews` into a dedicated table (per the PDF's recommended schema) rather than polluting the `orders` fact table. Second, the exact row counts (25k customers, 1,175 products, 138,116 orders, 397,569 items) and revenue ($177.13M) become the automated reconciliation test suite to verify our bulk `COPY` loader."*

* **Q: "How does this EDA inform your Machine Learning approach in Phase 5?"**
  * **A**: *"Three ways: (1) Verified the 2021–2025 date span, allowing a clean time-based split (train on 2021–2024, test on 2025) to avoid future-lookahead data leakage. (2) Confirmed the 6.85% class imbalance, establishing PR-AUC as the primary metric. (3) Identified key predictive signals: category historical return rate, discount amount, shipping latency, and customer repeat order history."*

* **Q: "How does this EDA connect to the RAG Assistant in Phase 8?"**
  * **A**: *"The RAG assistant is evaluated on grounded business questions ('Which category has the highest return rate?', 'What are the major patterns in ratings?'). The exact numbers, distributions, and insights computed in this EDA directly become the ground-truth knowledge base documents (`business_metrics.md`, `product_analysis.md`, `regional_analysis.md`) chunked and indexed into pgvector."*

---

### 3. Step-by-Step EDA Execution Playbook (What We Did, Why, & Interview Defense)

Here is the exact cell-by-cell walkthrough of how `notebooks/eda.ipynb` was designed and executed, detailing what operations were performed, what findings emerged, and how to defend each decision in an engineering interview.

```
+----------------------------------------------------------------------------------------------------+
|                                    EDA EXECUTION ARCHITECTURE                                      |
+----------------------------------------------------------------------------------------------------+
|  1. Setup & Ingestion   -->  Load 5 CSVs, profile shapes, verify dtypes & memory footprint          |
|  2. Temporal Parsing    -->  Parse order_date (2021-01-01 to 2025-06-30), derive Year/Month        |
|  3. Reconciliation      -->  Cross-check net_sales ($177.13M) vs dataset_statistics.csv (100% match)|
|  4. Structural Nulls    -->  Prove 24,557 missing ratings/days == 100% Cancelled/Unfulfilled       |
|  5. Target Exploration  -->  Analyze return_status: 9,462 returned (6.85%), formulate PR-AUC metric|
|  6. Dimensions Analysis -->  Profile Customers (25k), Products (1,175), Line Items (397,569)        |
|  7. Multidimensional    -->  Slice revenue & return rates by Category, Region, Marketing Channel    |
|  8. Quality Audits      -->  Audit negative values, margin anomalies, and dataset errata           |
|  9. Visualizations      -->  Seaborn monthly revenue trends, return rate bars, correlation matrix   |
+----------------------------------------------------------------------------------------------------+
```

#### Step 1: Environment Setup & Clean Data Science Conventions (Cell 1)
* **What We Did**: Imported standard numerical and visualization libraries (`pandas`, `numpy`, `matplotlib.pyplot`, `seaborn`), set plotting aesthetics (`sns.set_theme(style="whitegrid")`), and suppressed deprecation warnings.
* **Why We Did It**: Follows pure exploratory data science best practices. Instead of wrapping logic into opaque class methods or monolithic functions, kept operations cell-by-cell so every transformation is visible and inspectable.
* **Interview Defense Point**: *"In an EDA notebook, readability and reproducible cell-by-cell output take precedence over software engineering abstractions. Writing pure Pandas/NumPy pipeline steps makes the analytical trajectory immediately auditable by stakeholders."*

#### Step 2: Ingesting All 5 Datasets & Profiling Initial Dimensions (Cells 2–4)
* **What We Did**: Loaded `orders.csv` (138,116 rows, 13 cols), `order_items.csv` (397,569 rows, 6 cols), `customers.csv` (25,000 rows, 8 cols), `product_catalog.csv` (1,175 rows, 7 cols), and `dataset_statistics.csv` (11 rows). Inspected `.shape`, `.info()`, and `.head()`.
* **What The Data Showed**:
  * Total Orders: **138,116** transactions.
  * Total Line Items: **397,569** items (~2.88 items per order basket).
  * Unique Customers: **25,000** distinct profiles.
  * Product Catalog: **1,175** distinct SKUs.
* **Interview Defense Point**: *"Notice the cardinality relationships: 1 Customer has Many Orders (average ~5.5 orders/customer), and 1 Order has Many Order Items (~2.88 items/order). Inspecting shapes immediately reveals the entity-relationship hierarchy needed for our normalized Postgres schema in Phase 3."*

#### Step 3: Date Parsing & Temporal Horizon Verification (Cells 5–6)
* **What We Did**: Converted `order_date` using `pd.to_datetime(df_orders['order_date'])`, extracted `order_year`, `order_month`, and `order_year_month`. Checked `.min()` and `.max()`.
* **What The Data Showed**:
  * Minimum Date: **2021-01-01**
  * Maximum Date: **2025-06-30**
  * Total Span: Exactly **4.5 years** (54 calendar months) of continuous transaction records.
* **Interview Defense Point**: *"Verifying the 2021–2025 date range gives us the foundation for a strict time-based train/test split for Machine Learning (Phase 5). Instead of a random K-Fold split which causes future-lookahead data leakage, we train on 2021–2024 (4 years) and test on 2025 (6 months), simulating a true production forecasting environment."*

#### Step 4: Ground-Truth Financial Reconciliation (`net_sales` vs `gross_sales`) (Cells 7–10)
* **What We Did**: Calculated corporate aggregates across `df_orders` (`SUM(net_sales)`, `SUM(gross_sales)`, `SUM(profit)`, `AVG(net_sales)`, `SUM(discount_amount)`) and compared them directly against the published benchmark in `dataset_statistics.csv`.
* **What The Data Showed**:
  * **Net Sales Sum**: **$177,134,263.74** — Exact 100.00% match with published benchmark ($177.13M).
  * **Gross Sales Sum**: **$189,964,286.06** — Exceeds published benchmark by **$12,830,022.32 (+7.24%)**.
  * **Total Profit Sum**: **$43,767,888.89** — Exact match with published benchmark ($43.77M).
  * **Average Order Value (AOV)**: **$1,282.50** on `net_sales` — Exact match with published benchmark ($1,282.50).
  * **Total Discounts Given**: **$13,500,432.22** (~7.1% discount intensity across the business).
* **Interview Defense Point**: *"This was the most critical financial finding of the EDA. Gross sales overstates revenue by $12.83M because it ignores promotional voucher discounts. Building this reconciliation step protects downstream SQL analytics and executive dashboards from reporting inflated financial metrics. All revenue queries must use `net_sales`."*

#### Step 5: Missingness Audit & The 24,557 Structural Nulls Investigation (Cells 11–13)
* **What We Did**: Queried `df_orders.isnull().sum()` across all columns, then cross-tabulated missing values against `delivery_status` using boolean masking: `df_orders[df_orders['delivery_days'].isnull()]['delivery_status'].value_counts()`.
* **What The Data Showed**:
  * `delivery_days`: Exactly **24,557** missing values (17.78%).
  * `customer_rating`: Exactly **24,557** missing values (17.78%).
  * `review_sentiment`: Exactly **24,557** missing values (17.78%).
  * All other 10 columns: **0** missing values (100% complete).
  * Cross-tabulation: **100% (24,557 out of 24,557)** of these nulls have `delivery_status == 'Cancelled'` (or Pending/Unfulfilled).
* **Interview Defense Point**: *"Junior analysts often see nulls and immediately run `df.dropna()` or impute with `df.fillna(df.mean())`. In an interview, explain why that would be disastrous here: an order cancelled before shipping cannot logically have a delivery duration or a post-delivery customer satisfaction rating. These are structural, domain-valid state transitions. In Phase 3, we normalize `ratings` into its own table to eliminate sparse null columns from the main orders table."*

#### Step 6: Target Variable Exploration & Class Imbalance Strategy (`return_status`) (Cells 14–16)
* **What We Did**: Queried value counts, percentages, and cross-tabulations on `return_status`.
* **What The Data Showed**:
  * `Not Returned`: **128,654 orders (93.15%)**
  * `Returned`: **9,462 orders (6.85%)**
  * Class Imbalance Ratio: **13.6 to 1**.
* **Interview Defense Point**: *"With a 6.85% positive class, accuracy is a vanity metric: a trivial dummy model that predicts 'Not Returned' for every single order achieves 93.15% accuracy while providing zero business value. In Phase 5, we must evaluate our classification model using Precision-Recall AUC (PR-AUC), F1-Score, and Recall at key decision thresholds, and balance the loss function using `scale_pos_weight` or class weighting."*

#### Step 7: Customer Dimension Profiling (Cells 17–18)
* **What We Did**: Profiled customer distributions, age ranges, gender distributions, and geographic segmentation.
* **What The Data Showed**:
  * 25,000 unique customers across 5 geographic regions:
    * South: 5,142 (20.57%)
    * North: 5,039 (20.16%)
    * Central: 4,968 (19.87%)
    * West: 4,948 (19.79%)
    * East: 4,903 (19.61%)
  * Remarkable geographic balance (~20% per region).
  * Zero missing values in customer profiles.
* **Interview Defense Point**: *"The customer base is geographically uniform, meaning regional variance in revenue is driven by regional purchasing power and product preferences rather than customer acquisition volume."*

#### Step 8: Product Catalog Profiling & Catching Dataset Errata (Cells 19–21)
* **What We Did**: Profiled `product_catalog.csv`, checked category breakdowns, price distributions, and verified unique product IDs against `dataset_statistics.csv`.
* **What The Data Showed**:
  * 1,175 distinct products across 8 major categories.
  * Price range: $10.50 to $2,499.00 with a right-skewed log-normal distribution.
  * **Dataset Errata Discovery**: In `dataset_statistics.csv`, the row labeled `Total Products Used` states `138,116`. That number is an exact copy-paste duplicate of `Total Transactions`. The real unique product count across both catalog and transactions is **1,175**.
* **Interview Defense Point**: *"Catching this discrepancy shows true data stewardship. When an interviewer asks 'Have you ever found issues in a dataset provided by a client or upstream team?', cite this exact example: verifying column definitions against primary keys prevented downstream schema and documentation errors."*

#### Step 9: Order Items Granularity & Join Collision Prevention (Cells 22–24)
* **What We Did**: Investigated the line items table (`order_items.csv`), analyzed items-per-order distributions, and linked line items to product categories.
* **What The Data Showed**:
  * 397,569 total items across 138,116 orders.
  * Average basket size: 2.88 items per order.
  * **Engineering Gotcha Solved**: Both `order_items` and `orders` carry a `discount_amount` column. Merging them directly created `discount_amount_x` and `discount_amount_y`. We isolated category-order associations via an intermediate map `df_items[['order_id', 'product_id']].merge(df_products[['product_id', 'product_category']]).drop_duplicates('order_id')`, preventing merge collisions.
* **Interview Defense Point**: *"When joining denormalized flat files, column collisions can silently corrupt calculations. Creating explicit, minimal mapping projections before joining ensures clean, collision-free feature joins."*

#### Step 10: Multi-Dimensional Business Cuts (Cells 25–28)
* **What We Did**: Computed return rates, revenue, and order volumes across Product Categories, Regions, and Marketing Channels.
* **What The Data Showed**:
  * **Category Return Rates**:
    * Health & Wellness: **7.56%** (Highest risk)
    * Automotive: **7.34%**
    * Electronics: **7.16%**
    * Books & Media: **7.08%**
    * Clothing: **6.94%**
    * Home & Kitchen: **6.78%**
    * Baby & Kids: **6.49%**
    * Beauty & Personal Care: **6.30%** (Lowest risk)
  * **Category Revenue Dominance**:
    * Electronics ($35.8M) and Clothing ($32.1M) generate over **38% of all corporate revenue**.
  * **Delivery Status**:
    * Delivered: **113,559 (82.2%)**
    * Cancelled: **24,557 (17.8%)**
* **Interview Defense Point**: *"Demonstrates that product category is a potent predictor of return risk: a customer purchasing Health & Wellness is ~20% more likely to return their item than one purchasing Beauty & Personal Care. This justifies prioritizing category embeddings and one-hot features in our ML feature pipeline."*

#### Step 11: Anomaly, Outlier & Domain Logic Audits (Cells 29–30)
* **What We Did**: Screened for negative delivery days, negative profit transactions, and cross-validated delivery status vs return status.
* **What The Data Showed**:
  * Negative Delivery Days: **0 instances** (clean fulfillment data).
  * Negative Profit: Found in ~4.2% of transactions where aggressive promotional discounts (>35%) exceeded gross margin. This is realistic commercial behavior (loss-leader promotions).
  * Cancellation vs Return Consistency: Zero orders with `delivery_status == 'Cancelled'` have `return_status == 'Returned'`. The fulfillment lifecycle is logically sound.
* **Interview Defense Point**: *"Checking domain consistency rules confirms that the dataset reflects realistic e-commerce operations rather than synthetic noise. Understanding why negative profits happen (loss-leader discounts) shows commercial acumen."*

#### Step 12: Visualizations & Exploratory Correlation Matrix (Cells 31–33)
* **What We Did**: Plotted monthly revenue trends (2021–2025), return rate comparison bar charts, and a Pearson correlation heatmap across numeric attributes.
* **What The Data Showed**:
  * Monthly Revenue Trend shows healthy recurring Q4 seasonality (holiday shopping peaks in November/December) and consistent mid-year promotional bumps.
  * Correlation heatmap reveals strong positive correlation between `gross_sales` and `net_sales` (0.97), moderate positive correlation between `net_sales` and `profit` (0.78), and slight positive correlation between `discount_amount` and `return_status`.
* **Interview Defense Point**: *"Exploratory visualizations validate macro trends before model training. The correlation matrix confirms that discount depth correlates with return propensity, giving us our first hypothesis for feature engineering."*

---

### 4. Direct Architectural Bridges: How EDA Dictates Every Downstream Phase

```
+----------------------------------------------------------------------------------------------------+
|                                HOW EDA GUIDES THE REST OF THE STACK                                |
+----------------------------------------------------------------------------------------------------+
|  Phase 3: Database & Ingestion  --> Split ratings into 5th table; verify 138k rows & $177M via COPY  |
|  Phase 4: SQL Analytics Queries --> Filter on net_sales for revenue; handle cancelled order states  |
|  Phase 5: Machine Learning     --> Temporal split (2021-24 vs 2025); optimize PR-AUC for 6.85% returns |
|  Phase 6: FastAPI Endpoints    --> Pydantic validation handles null ratings on cancelled orders     |
|  Phase 7: OpenRouter Reports   --> Deterministic SQL feeds revenue; LLM interprets category risks    |
|  Phase 8: RAG Assistant        --> Embed verified $177M KPI and 7.56% category risk into pgvector   |
+----------------------------------------------------------------------------------------------------+
```

1. **Bridge to Phase 3 (Database Schema & Bulk Data Load)**:
   * **Exact Row Count Verification**: We know the exact record counts to verify our bulk `COPY` loading script: 25,000 customers, 1,175 products, 138,116 orders, and 397,569 line items.
   * **Dedicated `ratings` Table**: Because 24,557 orders lack ratings due to cancellations, splitting `ratings / reviews` into a dedicated table with an `order_id` foreign key ensures the core `orders` table remains dense and normalized.
2. **Bridge to Phase 4 (SQL Analytics Queries)**:
   * **Revenue Formulas**: Confirms that all financial analytics queries (top customers, regional sales, category breakdown) must compute `SUM(net_sales)` and `AVG(net_sales)`, not `gross_sales`.
   * **Status Filtering**: Queries evaluating delivery performance or customer ratings must explicitly include `WHERE delivery_status = 'Delivered'` to prevent skewing averages with cancelled orders.
3. **Bridge to Phase 5 (Machine Learning Pipeline)**:
   * **Data Leakage Prevention**: We establish a time-based train/test split: orders from **2021–2024** form the training set (~110k orders), and orders from **2025** form the test set (~28k orders).
   * **Evaluation Metrics**: Class imbalance (6.85%) mandates using **PR-AUC**, Precision, and Recall rather than standard accuracy or ROC-AUC.
   * **Feature Selection**: Category return risk (7.56% vs 6.30%), discount percentage, customer order history, and product price are confirmed as high-signal features.
4. **Bridge to Phase 6 (FastAPI REST Service)**:
   * **Pydantic Schemas**: Schemas must allow optional `delivery_days`, `customer_rating`, and `review_sentiment` fields (nullable) when returning order details.
   * **Business Validation**: Endpoints updating an order's status to 'Cancelled' must automatically enforce that ratings cannot be submitted.
5. **Bridge to Phase 7 (OpenRouter Executive Reports)**:
   * **Strict Prompt Architecture**: Prompts will strictly inject deterministic SQL outputs (e.g., "$177,134,263.74 total revenue, 6.85% return rate") into the LLM context, instructing the model to synthesize strategic narrative rather than calculate arithmetic.
6. **Bridge to Phase 8 (RAG Knowledge Assistant)**:
   * **Grounded Knowledge Base**: We compile the exact numerical findings from this EDA into structured markdown documents (`business_metrics.md`, `category_performance.md`, `logistics_and_returns.md`) to be chunked, embedded, and stored in `pgvector`. This guarantees 100% factual accuracy when users ask the RAG assistant about company KPIs.

---

### 5. Tough Interview Scenarios & Rapid-Fire Defense

* **Q: "If an executive asks you why Q3 revenue dropped by 5%, how would you dissect it based on this dataset?"**
  * **A**: *"I would decompose revenue into its fundamental formula: `Net Revenue = Order Volume × Average Basket Size × Average Item Price - Total Discounts`. First, check if order volume dropped (customer acquisition or website traffic issue). Second, check basket size (cross-selling efficiency). Third, check if discount spending was cut or if product category mix shifted from high-AOV Electronics to lower-AOV Clothing. Finally, check fulfillment rates—did cancellations increase due to logistics bottlenecks?"*

* **Q: "Why did you run EDA in a Jupyter Notebook using Pandas rather than writing SQL queries directly against Postgres?"**
  * **A**: *"Both have distinct roles. Pandas in Jupyter allows rapid, iterative exploration, distribution plotting (Seaborn), and correlation matrix computation without schema constraints. It also allows us to audit the raw CSVs *before* database ingestion, ensuring our Postgres DDL and constraints reflect the true reality of the source data. Once patterns are verified, we transition to SQL for scalable, persistent storage and production analytics."*

* **Q: "How would your EDA pipeline scale if this dataset grew from 138,000 rows to 100 Million rows?"**
  * **A**: *"Pandas operates in-memory and would hit RAM limits at 100M rows (~50GB+ in memory). I would scale using three strategies: (1) Out-of-core query engines like **DuckDB** or **Polars** with lazy evaluation, which execute streaming queries on parquet files with minimal memory footprint. (2) Push aggregations down into PostgreSQL or Snowflake using SQL GROUP BY operations. (3) For ML distribution checks, use stratified sampling (e.g., 1M representative rows) to profile distributions before training on a distributed engine like Spark."*

* **Q: "What data quality issues in this dataset would cause you to reject a data ingestion pipeline in production?"**
  * **A**: *"Three critical issues would trigger pipeline rejection: (1) Negative values in non-negative fields like `net_sales` or `delivery_days`. (2) Orphan records—order line items referencing a `product_id` or `order_id` that doesn't exist in parent tables. (3) State contradictions—such as an order marked as `Cancelled` having a 5-star customer rating or a positive `delivery_days` value. Catching these at ingestion prevents downstream model corruption."*




