"""
ml/predict.py — load the trained model, transform a raw order into the
model's feature space, predict a return probability, and attach a
lightweight rule-based "contributing factors" explanation.

Imported by `app/api/ml.py`, not run directly — it has no
`if __name__ == "__main__"` block.

Model + metadata are loaded ONCE at import time (module-level globals), not
per-request — `joblib.load`/reading `metadata.json` on every request would
be wasted, repeated I/O for data that never changes between requests.
"""
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

ML_DIR = Path(__file__).resolve().parent
MODEL_PATH = ML_DIR / "model.joblib"
METADATA_PATH = ML_DIR / "metadata.json"

model = joblib.load(MODEL_PATH)
with open(METADATA_PATH) as f:
    metadata = json.load(f)

FEATURE_COLUMNS: list[str] = metadata["features"]["all_columns_in_order"]
CATEGORICAL_FEATURES: list[str] = metadata["features"]["categorical"]
NUMERIC_FEATURES: list[str] = metadata["features"]["numeric"]
BINARY_FEATURES: list[str] = metadata["features"]["binary"]
CATEGORICAL_CATEGORIES: dict[str, list[str]] = metadata["features"]["categorical_categories"]
RISK_STATS = metadata["risk_reference_stats"]

# Fallback for a `customer_id` this API has never seen before (no rows in
# `customers`/`orders` yet) - defaulting rather than 404ing, since scoring a
# brand-new customer (e.g. at their very first checkout) is a legitimate,
# common real-world use of this endpoint, not an error condition.
# "Consumer" is the training data's most common segment (13,638/24,911
# customers - confirmed by direct query, not assumed from the column name).
DEFAULT_CUSTOMER_SEGMENT = "Consumer"

# Absolute percentage-point margin above the overall training return rate
# needed before a categorical value is called out as a contributing factor.
# Chosen deliberately, not left at "any amount above average": these
# category/channel/etc. return rates all cluster tightly (roughly 6.2%-7.3%
# across every categorical feature - see metadata.json's
# risk_reference_stats), so a zero-margin rule would flag most categories on
# essentially noise-level differences. 0.3 percentage points surfaces the
# handful of categories with a real, if still modest, gap (e.g. Jewelry/
# Automotive/Grocery among primary_category, PayPal among payment_method)
# without manufacturing a "risk factor" out of a rounding-level difference.
CATEGORY_RISK_MARGIN = 0.003


# ----------------------------------------------------------------------------
# Model loading, input transformation, and prediction
# ----------------------------------------------------------------------------
def _get_customer_segment(db: Session, customer_id: str) -> str:
    """Look up the customer's segment - not something a checkout request
    should have to supply itself, since it's a stored customer attribute,
    not an order attribute, and the model was trained on it the same way.
    """
    row = db.execute(
        text("SELECT customer_segment FROM customers WHERE customer_id = :customer_id"),
        {"customer_id": customer_id},
    ).fetchone()
    return row[0] if row else DEFAULT_CUSTOMER_SEGMENT


def _get_customer_history(db: Session, customer_id: str) -> tuple[int, float, int]:
    """Point-in-time customer history, matching how the training features
    were built.

    Simpler here than at training time: this order hasn't been placed yet,
    so every existing row for this `customer_id` is by definition prior
    history as of right now — no date filter is needed, unlike the
    cumulative counts computed over rows that all already existed.

    A `customer_id` with no rows yet (a brand-new customer) is not an
    error; it correctly yields (0, 0.0, 0), the same "first order" state
    every customer had on their own first order in training.
    """
    row = db.execute(
        text(
            "SELECT COUNT(*), COALESCE(SUM(net_sales), 0) FROM orders WHERE customer_id = :customer_id"
        ),
        {"customer_id": customer_id},
    ).fetchone()
    prior_order_count, prior_revenue = row
    is_repeat = 1 if prior_order_count > 0 else 0
    return int(prior_order_count), float(prior_revenue), is_repeat


def build_feature_row(order: dict[str, Any], db: Session) -> pd.DataFrame:
    """Turn one raw order (the API request body, as a plain dict) into a
    single-row DataFrame in the model's tree-format - same column order,
    same `category` dtype with the same trained category vocabulary
    (`categorical_categories` in the saved metadata) as training, so the model reads
    categories identically at serve time as it did at fit time.
    """
    # Pydantic's gt=0 already rejects this at the API layer; kept as a guard
    # for direct callers of this module (tests, notebooks) that bypass it.
    if order["gross_sales"] <= 0:
        raise ValueError("gross_sales must be positive - shipping_ratio would divide by zero")

    prior_count, prior_revenue, is_repeat = _get_customer_history(db, order["customer_id"])
    customer_segment = _get_customer_segment(db, order["customer_id"])
    # Post-fulfillment and outcome-proxy fields (such as discounts) are excluded
    # to maintain strict pre-order checkout inference.
    row = {
        "shipping_ratio": order["shipping_cost"] / order["gross_sales"],
        "sales_channel": order["sales_channel"],
        "payment_method": order["payment_method"],
        "shipping_method": order["shipping_method"],
        "region": order["region"],
        "customer_segment": customer_segment,
        "primary_category": order["primary_category"],
        "customer_prior_order_count": prior_count,
        "customer_prior_revenue": prior_revenue,
        "is_repeat_customer_asof": is_repeat,
    }
    X = pd.DataFrame([row], columns=FEATURE_COLUMNS)

    # Pin each categorical column to the EXACT trained category order - not
    # a plain `.astype("category")`, which would let pandas infer categories
    # from this single request row alone and silently assign different
    # internal codes than training used, quietly corrupting the prediction.
    for col in CATEGORICAL_FEATURES:
        X[col] = pd.Categorical(X[col], categories=CATEGORICAL_CATEGORIES[col])
        if X[col].isna().any():
            raise ValueError(
                f"'{order[col]!r}' is not a value {col} ever took in training "
                f"(expected one of {CATEGORICAL_CATEGORIES[col]})"
            )
    return X


def predict_return_probability(order: dict[str, Any], db: Session) -> tuple[float, pd.DataFrame]:
    """Returns (probability of return, the feature row used) - the feature
    row is returned alongside so the explanation heuristic can inspect the same
    values just fed to the model, instead of recomputing them a second
    time.
    """
    X = build_feature_row(order, db)
    probability = float(model.predict_proba(X)[0, 1])
    return probability, X


# ----------------------------------------------------------------------------
# Rule-based "contributing factors" heuristic (deliberately not SHAP)
# ----------------------------------------------------------------------------
# Rule-based contributing factors heuristic grounded in empirical baseline
# statistics (`risk_reference_stats`, computed from the training split in ml/train.py).
# Decoupled from specific model internals (SHAP/coefficients) to ensure consistent,
# interpretable business reasoning across model iterations without adding heavy dependencies.
def explain_contributing_factors(X: pd.DataFrame) -> list[str]:
    row = X.iloc[0]
    factors: list[str] = []
    overall_rate = RISK_STATS["overall_train_return_rate"]

    for col in CATEGORICAL_FEATURES:
        value = str(row[col])
        category_rate = RISK_STATS["category_return_rates"][col].get(value)
        if category_rate is not None and category_rate - overall_rate >= CATEGORY_RISK_MARGIN:
            factors.append(
                f"{col}='{value}' has a historical return rate of {category_rate:.2%}, "
                f"above the overall training average of {overall_rate:.2%}."
            )

    for col in NUMERIC_FEATURES:
        value = float(row[col])
        p75 = RISK_STATS["numeric_quantiles"][col]["p75"]
        if value > p75:
            factors.append(
                f"{col}={value:.4g} is in the top quartile of training orders "
                f"(75th percentile threshold: {p75:.4g})."
            )

    # is_repeat_customer_asof deliberately excluded: the training data shows
    # essentially no difference in return rate between new and repeat
    # customers (see metadata.json's repeat_customer_return_rates - both
    # ~6.77-6.78%), so flagging it here would manufacture a signal that
    # this dataset doesn't actually show.

    if not factors:
        factors.append(
            "No individually elevated risk factors identified for this order - "
            "its feature values are close to the overall training averages."
        )
    return factors
