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
