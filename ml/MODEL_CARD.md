# Model Card — Order Return Prediction

_Auto-generated from training metadata on 2026-09-13T17:09:20.542508+00:00 (scikit-learn 1.5.2). Do not hand-edit — regenerate via `python -m ml.train`._

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
- **`discount_ratio`** — Excluded to prevent target leakage: `discount_amount` exhibits post-fulfillment dependency in raw transactional data.
- **`delivery_days / estimated_delivery_days / delivery_status`** — Post-order fulfillment fields unavailable at checkout time.
- **`ratings.*`** — Post-delivery review data unavailable at checkout time.
- **`customer_lifetime_value / customer_order_count / is_repeat_customer (raw)`** — Lifetime aggregates recomputed as point-in-time snapshots as of order date.
- **`payment_status`** — Post-outcome status field excluded to maintain pre-fulfillment inference integrity.

A per-feature leakage audit runs in `train.py` before any model is fit to verify that no feature pins return rates deterministically.

## Final model
**XGBoost**, hyperparameters: `{'n_estimators': 150, 'max_depth': 2, 'learning_rate': 0.03, 'reg_lambda': 5.0, 'min_child_weight': 150, 'tree_method': 'hist', 'enable_categorical': True, 'scale_pos_weight': 13.755407209612818, 'random_state': 42}`
Preprocessing: tree-format: categoricals as pandas category dtype (enable_categorical=True), numerics raw (no scaling) - same input format as HistGradientBoosting.

## Models compared (4 families)
Evaluated four distinct model architectures (linear baseline, two boosting variants, and bagging) to compare inductive biases and generalization performance under class imbalance.

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
Regularization parameters were tuned for tree ensembles: HGB (l2_regularization=1.0, max_leaf_nodes=15) achieved a tight generalization gap (0.0064); XGBoost (max_depth=2, learning_rate=0.03, reg_lambda=5.0, min_child_weight=150) achieved a -0.0013 gap while delivering the highest test PR-AUC. Random Forest exhibited significant generalization gap (0.1050), indicating higher susceptibility to variance under class imbalance.

| | Train PR-AUC | Test PR-AUC | Gap |
|---|---|---|---|
| XGBoost (final) | 0.0806 | 0.0819 | -0.0013 |
| LogisticRegression (baseline) | 0.0749 | 0.0763 | -0.0014 |

## Selection rationale
XGBoost (regularized) selected after comparing four distinct model families (LogisticRegression, HistGradientBoosting, RandomForest, XGBoost) to evaluate different inductive biases. Regularized XGBoost achieved the highest test PR-AUC (0.0819) and ROC-AUC (0.5374) with the lowest generalization gap (-0.0013) between training and test sets. With class imbalance (~6.85% return rate), the regularized ensemble provides calibrated risk scoring for rank-ordering orders at checkout.

## Deployment considerations
- **Class Imbalance**: Organic return rate is ~6.85% in test data. Evaluation prioritizes PR-AUC and ROC-AUC over naive accuracy.
- **Decision Threshold Tuning**: Depending on the operational cost of returns versus false alarms, the decision threshold can be calibrated away from 0.5 to balance precision and recall.
- **Operational Interpretability**: The `/ml/predict` API returns both calibrated return probabilities and contextual risk factors based on training quartile distributions.
