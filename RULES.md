# Rules — binding for any agent (AI or human) working on this repo

These rules exist because of a real incident: an earlier session built five
phases of this project unattended between check-ins, which produced working
code but left the person who has to defend it in an interview unable to
explain what happened or why. These rules fix that.

## 1. Logging is not optional
Every non-trivial decision, deviation, bug, or environment gotcha gets an
entry in [INTERVIEW_PREP.md](INTERVIEW_PREP.md) **the moment it happens** —
not reconstructed from memory afterward, not batched at the end of a phase.
If you're unsure whether something is worth logging, log it. This is the
most important rule in this file; everything else supports it.

## 2. No unapproved coding
Do not create, edit, run, or delete any code, config, infrastructure (files,
Docker, DB, git operations) without the user's explicit go-ahead for that
specific step. Drafting or updating docs/plans/logs for review is the
exception.

## 3. One task at a time, explained before it starts
Follow [TASKS.md](TASKS.md) in order — it's the atomic breakdown of
[SCOPE.md](SCOPE.md)'s phases. Before starting a task (or a small,
explicitly-agreed batch of them), restate what it involves and any real
decision in it, then wait for explicit approval. After finishing, check the
box in `TASKS.md`, stop, and report — do not chain into the next task
automatically, even if the previous approval sounded open-ended.

## 4. No silent scope changes
If a better idea comes up mid-build, propose it and log the trade-off —
don't just implement it. `SCOPE.md` is the single source of truth for what's
in and out; update its change log when something is approved to change.

## 5. Verify, don't assume
Any computed number (revenue, counts, metrics, model scores) must be
cross-checked against an independent source (a second computation path, a
published ground truth, a reconciliation query) before being treated as
correct. Mismatches get logged and resolved before moving on — see the
net_sales-vs-gross_sales incident in `INTERVIEW_PREP.md` for why this rule
exists.

## 6. Destructive actions always need explicit confirmation
Deleting files, wiping git history, dropping DB volumes/containers,
force-pushing — always ask first, even if a similar action was approved
minutes ago. Approval doesn't carry over between actions.

## 7. Secrets and large files never get committed
`.env` (and any real credentials/keys) stay local and out of git. Before
committing after adding a new data/output directory, verify `.gitignore`
actually matches the real nested path — a pattern like `data/*.csv` does
**not** match `data/dataset/*.csv`; use `data/**/*.csv` or check with
`git status` first.

## 8. Explain, don't just do
Every implementation choice (schema design, model choice, prompt design,
library pick) must be explainable in plain language. If it can't be
explained simply, simplify it or write down the reasoning until it can —
this project exists to be defended in an interview, not just to run.

## 9. The user is the decision-maker
When a technical choice has real trade-offs, surface the options and ask —
don't pick silently and move on. Recommending an option is fine and
encouraged; deciding unilaterally on anything with a real trade-off is not.
