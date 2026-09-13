# Model Card — Order Return Prediction

_Auto-generated from training metadata on 2026-09-13T08:36:14.282197+00:00 (scikit-learn 1.5.2). Do not hand-edit — regenerate via `python -m ml.train`._

## Problem
Order Return Prediction (binary classification: order_status == 'Returned')

Return rate in the full dataset: ~6.85% — a real class imbalance, which is why PR-AUC (not accuracy or ROC-AUC alone) is the primary evaluation metric throughout.

## Data split (time-based, not random)
| | Period | Rows | Return rate |
|---|---|---|---|
| Train | 2021-01-01 to 2024-12-31 | 110,518 | 6.78% |
| Test | 2025-01-01 to 2025-12-31 | 27,598 | 7.15% |

A random split was rejected in favor of this one: it would leak future information into training and doesn't match how the model would actually be used (scoring new orders using only what happened before them).

## Features
- **Numeric** (3): shipping_ratio, customer_prior_order_count, customer_prior_revenue
- **Categorical** (6): sales_channel, payment_method, shipping_method, region, customer_segment, primary_category
- **Binary** (1): is_repeat_customer_asof

### Deliberately excluded (and why)
- **`discount_ratio`** — TARGET LEAK - discount_amount is 0 for 100% of Returned and Cancelled orders and >0 for ~100% of Completed orders (data-generation artifact). Found at T114, removed; every metric here is from the leak-free retrain.
- **`delivery_days / estimated_delivery_days / delivery_status`** — NULL/'Cancelled' for 100% of returned orders - leaks the outcome (T098).
- **`ratings.*`** — 0 of 9,462 returned orders ever have a rating, by construction (T093).
- **`customer_lifetime_value / customer_order_count / is_repeat_customer (raw)`** — lifetime aggregates, not point-in-time snapshots (T100); recomputed as-of-order instead.
- **`payment_status`** — 'Refunded' <=> Returned - a post-outcome field, never a candidate.

A per-feature leakage audit now runs in `train.py` before any model is fit: no single value (categorical) or decile (numeric) of any feature may pin the return rate to exactly 0% or 100%. It was added after `discount_ratio` passed every earlier check (nulls, ranges, cardinality) while being an almost-deterministic proxy for the outcome.

## Final model
**XGBoost**, hyperparameters: `{'n_estimators': 150, 'max_depth': 2, 'learning_rate': 0.03, 'reg_lambda': 5.0, 'min_child_weight': 150, 'tree_method': 'hist', 'enable_categorical': True, 'scale_pos_weight': 13.755407209612818, 'random_state': 42}`
Preprocessing: tree-format: categoricals as pandas category dtype (enable_categorical=True), numerics raw (no scaling) - same input format as HistGradientBoosting.

## Models compared (4 families)
Deliberately different inductive biases — a linear model, two boosting variants, and a bagging variant — to test whether weak performance was a model-choice problem before concluding it's a feature-ceiling problem (see Overfitting check + Selection rationale below).

| Model | Test PR-AUC | Test ROC-AUC | Train PR-AUC | Train/test gap | Verdict |
|---|---|---|---|---|---|
| LogisticRegression | 0.0763 | 0.5121 | 0.0749 | -0.0014 | Baseline |
| HistGradientBoosting | 0.0804 | 0.5362 | 0.0868 | +0.0064 |  |
| RandomForest | 0.0794 | 0.5323 | 0.1844 | +0.1050 |  |
| XGBoost | 0.0819 | 0.5374 | 0.0806 | -0.0013 | **SELECTED** |
| *random guess* | 0.0715 | 0.5000 | — | — | (floor) |

### Other models tried, not selected
- **HistGradientBoostingClassifier** (`{'categorical_features': 'from_dtype', 'class_weight': 'balanced', 'random_state': 42, 'l2_regularization': 1.0, 'max_leaf_nodes': 15}`) — Strong second place - beaten by XGBoost on every test metric by a small margin, with a slightly larger overfitting gap. Not rejected for cause, just edged out.
- **RandomForestClassifier** (`{'n_estimators': 300, 'max_depth': 8, 'class_weight': 'balanced', 'random_state': 42}`) — REJECTED - worse test PR-AUC than HGB/XGBoost (0.0794) AND the worst overfitting of any model tried (train/test gap 0.1050, ~16x XGBoost's).

## Baseline model (for comparison)
**LogisticRegression**, hyperparameters: `{'class_weight': 'balanced', 'max_iter': 1000, 'random_state': 42}`
Preprocessing: RobustScaler (numeric) + OneHotEncoder(handle_unknown='ignore') (categorical)

## Test-set metrics — final model vs. baseline (2025, held out)
| Metric | XGBoost (final) | LogisticRegression (baseline) |
|---|---|---|
| PR-AUC | 0.0819 | 0.0763 |
| ROC-AUC | 0.5374 | 0.5121 |
| Precision | 0.0779 | 0.0731 |
| Recall | 0.5487 | 0.5989 |
| F1 | 0.1364 | 0.1302 |

Confusion matrix (final model, 0.5 threshold): TN=12,812, FP=12,814, FN=890, TP=1,082

![ROC Curve](plots/roc_curve.png)
![Precision-Recall Curve](plots/pr_curve.png)
![Confusion Matrix](plots/confusion_matrix.png)

## Overfitting check
Regularization search run for both tree ensembles: HGB's l2_regularization=1.0/max_leaf_nodes=15 (vs. defaults 0/31) halved its gap (0.0134 -> 0.0064); XGBoost's max_depth=2/learning_rate=0.03/reg_lambda=5.0/min_child_weight=150 (vs. an initial default-ish fit with gap 0.0735) brought its gap to -0.0013 (test slightly exceeds train) while matching the best test PR-AUC seen across every variant tried. Random Forest was NOT regularization-rescued the same way - its gap (0.1050) was the reason it was rejected, not tuned further. Full detail in INTERVIEW_PREP.md 2026-09-13.

| | Train PR-AUC | Test PR-AUC | Gap |
|---|---|---|---|
| XGBoost (final) | 0.0806 | 0.0819 | -0.0013 |
| LogisticRegression (baseline) | 0.0749 | 0.0763 | -0.0014 |

## Selection rationale
XGBoost (regularized) selected after comparing FOUR model families (LogisticRegression, HistGradientBoosting, RandomForest, XGBoost) - deliberately including a linear model, two boosting variants, and a bagging variant to test whether the near-random result (see below) was a model-choice problem. It wasn't: all four converged to a tight 0.076-0.082 test PR-AUC band. XGBoost leads on every test metric (PR-AUC 0.0819 vs HGB's 0.0804, ROC-AUC 0.5374 vs 0.5362) with an even smaller train/test gap than HGB's already-small one. RandomForest was rejected outright: worse test PR-AUC AND by far the worst overfitting of any model tried. IMPORTANT CONTEXT: on the leak-free feature set, no model is much better than random (test PR-AUC ~0.08 vs. a 0.0715 base rate; ROC-AUC ~0.54 vs 0.5). The pre-fix 0.57 PR-AUC / 0.97 ROC-AUC was almost entirely the discount_ratio leak. Trying four different algorithms and landing in the same narrow band - including a high-capacity model failing to fit even the training data much better - is the evidence that this is a feature ceiling, not something a different or better-tuned algorithm would fix. The shipped model should be read as 'slightly better than the base rate', not as a confident risk score.

## Known limitations — read this before using the predictions
- **The model is only marginally better than random.** Test PR-AUC 0.0819 vs. a random-guess floor of 0.0715 (the test return rate); ROC-AUC 0.5374 vs. 0.5. On the legitimate pre-outcome features available in this dataset, returns are close to unpredictable — every categorical value's historical return rate sits within roughly 6.2–7.3%.
- **An earlier version of this pipeline reported PR-AUC 0.57 / ROC-AUC 0.97.** That was a target leak (`discount_ratio`, see exclusions above), found during API smoke testing and removed. Those numbers were not real model skill.
- At the 0.5 probability threshold with `class_weight="balanced"`, the model labels roughly half of all orders "Returned" (recall ≈ 0.55, precision ≈ 0.08). `predicted_label` from the API is therefore a weak signal; `return_probability` ranked across many orders is the more useful output.
- "Contributing factors" from the prediction API are a rule-based heuristic over raw feature values grounded in training-set rates, not derived from model internals (no SHAP/coefficients). Given how weak the model is, those historical rates are arguably more informative than the probability itself.
- Most promising next step is **more/better features, not tuning**: the raw-column scan during the leak audit showed order-size fields (`quantity`, `gross_sales`) with wider return-rate spread by decile than anything currently used.
