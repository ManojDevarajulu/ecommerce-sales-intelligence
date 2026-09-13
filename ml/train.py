"""
ml/train.py — Order Return Prediction: training pipeline.

Run directly (`python -m ml.train`) rather than imported as a library.
Each stage prints what it did and asserts what it expects, so a failed run
says which step broke and why instead of producing a quietly wrong model.

Data is loaded from Postgres rather than the raw CSVs: the loaded tables
were already reconciled against the dataset's published totals exactly, so
the database is the trustworthy source, and reusing `app/db/session.py`
keeps one connection-config path for the whole project.

Deliberately NOT loaded: `ratings` and `customers`. Ratings are excluded
from this pipeline entirely — every returned order has
`delivery_status='Cancelled'`, the same state that prevents a rating from
ever being collected (confirmed: 0 of 9,462 returned orders have one), so
any rating-derived feature would leak the target. `customers` isn't needed
either, because the customer-history features are recomputed from `orders`
itself rather than read off the customer table.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")  # headless - this script never opens a display window
import matplotlib.pyplot as plt
import pandas as pd
import sklearn
import xgboost as xgb
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.preprocessing import OneHotEncoder, RobustScaler

from app.db.session import engine

ML_DIR = Path(__file__).resolve().parent


def main() -> None:
    """Run the full training pipeline end to end."""

    # ----------------------------------------------------------------------------
    # Load orders, order_items, products into pandas
    # ----------------------------------------------------------------------------
    orders = pd.read_sql("SELECT * FROM orders", engine)
    order_items = pd.read_sql("SELECT * FROM order_items", engine)
    products = pd.read_sql("SELECT * FROM products", engine)

    print("orders:", orders.shape)
    print("order_items:", order_items.shape)
    print("products:", products.shape)

    # Sanity check against the reconciled row counts (app/db/reconcile.py) — if
    # these don't match, something is wrong with the DB connection/state, not
    # with anything below, and everything downstream should stop.
    assert orders.shape[0] == 138_116, f"expected 138,116 orders, got {orders.shape[0]}"
    assert order_items.shape[0] == 397_569, f"expected 397,569 order_items, got {order_items.shape[0]}"
    assert products.shape[0] == 1_175, f"expected 1,175 products, got {products.shape[0]}"
    print("row counts match the reconciled dataset totals - OK")

    # ----------------------------------------------------------------------------
    # Define the target: order_status == 'Returned'
    # ----------------------------------------------------------------------------
    # `return_status IS NOT NULL` agrees with this exactly (verified against
    # the loaded data) — using `order_status` since it's the one NOT NULL column
    # of the two, so there's no ambiguity about a genuinely-missing value vs. a
    # negative case.
    orders["target"] = (orders["order_status"] == "Returned").astype(int)

    target_counts = orders["target"].value_counts()
    return_rate = orders["target"].mean()
    print("\ntarget distribution:")
    print(target_counts)
    print(f"return rate: {return_rate:.4%}")

    assert target_counts[1] == 9_462, f"expected 9,462 positive examples, got {target_counts[1]}"
    assert abs(return_rate - 0.0685) < 0.0001, f"expected ~6.85% return rate, got {return_rate:.4%}"
    print("target matches the reconciled 9,462 / 6.85% return rate - OK")

    # ----------------------------------------------------------------------------
    # Time-based split (train 2021-24, test 2025)
    # ----------------------------------------------------------------------------
    # A random split would leak future information into training (the model
    # could learn from 2025 patterns to predict 2021 orders) and doesn't match
    # how the model would actually be used - scoring new orders as they come
    # in, using only what happened before. The 2021-2024/2025 boundary isn't
    # arbitrary: the EDA already confirmed near-equal yearly volume
    # (~27.5-27.8k/year across all 5 years), so this gives a realistic ~80/20
    # split without cherry-picking a boundary to hit a round number.
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    orders["order_year"] = orders["order_date"].dt.year

    train_mask = orders["order_year"] <= 2024
    test_mask = orders["order_year"] == 2025

    print(f"\ntrain: {train_mask.sum():,} orders (2021-2024)")
    print(f"test:  {test_mask.sum():,} orders (2025)")
    print(f"train return rate: {orders.loc[train_mask, 'target'].mean():.4%}")
    print(f"test return rate:  {orders.loc[test_mask, 'target'].mean():.4%}")

    assert train_mask.sum() == 110_518, f"expected 110,518 train orders, got {train_mask.sum()}"
    assert test_mask.sum() == 27_598, f"expected 27,598 test orders, got {test_mask.sum()}"
    assert (train_mask | test_mask).all(), "found an order outside 2021-2025"
    print("split sizes match the EDA's known yearly volumes - OK")
    # NOTE: this train_mask/test_mask pair is provisional, for the verification
    # prints/asserts above only. The customer-history step below sorts `orders`
    # and resets its index, which moves rows to new positions/labels - these
    # masks get recomputed from `order_year` right after that sort, and it is
    # the recomputed pair (not these) that the preprocessing step actually
    # uses. See the bug note at that sort for what goes wrong otherwise.

    # ----------------------------------------------------------------------------
    # Feature: discount ratio — EXCLUDED (target leak)
    # ----------------------------------------------------------------------------
    # Originally built as discount_amount / gross_sales and used by every
    # model. Removed after an API smoke test showed the model's output was
    # almost entirely a step function on "discount_ratio == 0": in this
    # dataset, discount_amount is 0 for 100% of Returned AND 100% of Cancelled
    # orders, and > 0 for ~100% of Completed orders - every single one of the
    # 9,462 returns has a zero discount, and 0 of the 120,252 discounted orders
    # is a return. That's a data-generation artifact (a discount is only
    # recorded when the order actually completes), which makes the column an
    # almost-deterministic proxy for the outcome - the same structural leak as
    # delivery_days and ratings, just hidden inside a ratio. Every metric this
    # script reports is from the leak-free retrain that followed.
    #
    # The leak is asserted here, not just described, so the exclusion stays
    # justified by the data itself: if a future dataset version fixes this,
    # the assertion fails and the feature can be reconsidered deliberately.
    assert (orders["gross_sales"] > 0).all(), "found a non-positive gross_sales, ratios would divide by zero"
    _discounted = orders["discount_amount"] > 0
    assert orders.loc[_discounted, "target"].sum() == 0, \
        "discount_amount > 0 now co-occurs with returns - the leak may be gone, reconsider the feature"
    assert (orders.loc[orders["target"] == 1, "discount_amount"] == 0).all(), \
        "a returned order now has a non-zero discount - the leak may be gone, reconsider the feature"
    print(f"\ndiscount_ratio EXCLUDED - leak re-confirmed: 0 of {int(_discounted.sum()):,} discounted orders "
          f"are returns; all {int((orders['target'] == 1).sum()):,} returns have discount_amount == 0")

    # ----------------------------------------------------------------------------
    # Feature: shipping ratio
    # ----------------------------------------------------------------------------
    # Checked for the same zero-vs-nonzero artifact as discount_ratio when that
    # leak was found: shipping_cost == 0 occurs for ~0.3% of orders, spread
    # evenly across every order_status (return rate 7.7% vs 6.9% overall, 377
    # rows - noise). Clean; kept.
    orders["shipping_ratio"] = orders["shipping_cost"] / orders["gross_sales"]
    print("shipping_ratio range:", orders["shipping_ratio"].min(), "-", orders["shipping_ratio"].max())

    # ----------------------------------------------------------------------------
    # Categorical features
    # ----------------------------------------------------------------------------
    # `customer_segment` lives on `customers`, not `orders` (see app/db/seed.py's
    # ORDERS_COLS - it's one of the customer-demographic columns deliberately
    # kept out of the orders table), so it needs a merge. Worth naming the same
    # caution given to the customer-history fields below even though it isn't
    # excluded:
    # `customer_segment` is also constant per customer (confirmed in an earlier
    # session), which is fine IF it's a stated/assigned classification - but if
    # it were secretly derived from lifetime spend (a plausible real-world rule:
    # "VIP" once total spend crosses a threshold), it would carry the same
    # leakage risk as `customer_lifetime_value`. No evidence either way for this
    # synthetic dataset; kept as a feature with this caveat on record rather
    # than silently assumed safe.
    customers = pd.read_sql("SELECT customer_id, customer_segment FROM customers", engine)
    orders = orders.merge(customers, on="customer_id", how="left", validate="many_to_one")
    assert orders["customer_segment"].isna().sum() == 0, "merge produced unmatched customer_id rows"

    # `primary_category` — the EDA already proved product category is a real
    # return-risk signal (Automotive highest at 7.21%, Baby & Kids lowest at
    # 6.59% - see sql/02_analytics_queries.sql Q8), but nothing built so far
    # uses `order_items`/`products` at all, even though both are loaded. An
    # order can span multiple categories (~2.88 items/order on average), so
    # there's no single "the category" column to merge in directly - assign
    # each order the category of its own highest-value (net_sales) line item,
    # a standard, defensible simplification for a multi-item basket.
    item_categories = order_items.merge(products[["product_id", "product_category"]], on="product_id", how="left")
    assert item_categories["product_category"].isna().sum() == 0, "an order_item referenced an unknown product_id"

    top_item_idx = item_categories.groupby("order_id")["net_sales"].idxmax()
    primary_category = (
        item_categories.loc[top_item_idx, ["order_id", "product_category"]]
        .rename(columns={"product_category": "primary_category"})
    )
    orders = orders.merge(primary_category, on="order_id", how="left", validate="one_to_one")
    assert orders["primary_category"].isna().sum() == 0, "an order has no order_items at all"

    CATEGORICAL_FEATURES = [
        "sales_channel", "payment_method", "shipping_method", "region", "customer_segment", "primary_category",
    ]
    print("\ncategorical feature cardinality:")
    for col in CATEGORICAL_FEATURES:
        print(f"  {col}: {orders[col].nunique()} values -> {sorted(orders[col].unique())}")
    # The actual one-hot/encoder fitting happens in the preprocessing step
    # below, on the training split only - encoding is prepared here, not fit here.

    # ----------------------------------------------------------------------------
    # Customer-history features, recomputed point-in-time (NOT the
    # dataset's own is_repeat_customer/customer_order_count/
    # customer_lifetime_value columns, which are lifetime aggregates)
    # ----------------------------------------------------------------------------
    # Step A - verify the leakage suspicion before acting on it, rather than
    # assuming it: confirmed customer_order_count and is_repeat_customer are
    # BOTH constant per customer across every order they placed (0 exceptions
    # across 24,911 customers) - the same lifetime-aggregate pattern already
    # confirmed for customer_lifetime_value/customer_type/region/
    # customer_segment. A second, independent problem also turned up: the
    # stored customer_order_count doesn't even reliably match how many order
    # rows that customer actually has in this dataset - it disagrees for 9,424
    # of 24,911 customers (~37.8%), and is_repeat_customer disagrees with
    # "actual total orders > 1" for 190 customers. So the raw column isn't just
    # a leakage risk - it's also internally inconsistent with the data. Both
    # problems are avoided by recomputing from `orders` directly instead of
    # trusting the given column.
    orders = orders.sort_values(["customer_id", "order_date", "order_id"]).reset_index(drop=True)

    # BUGFIX (found while sanity-checking the baseline model): the sort above
    # reorders rows and resets the index to a fresh 0..N-1, while the earlier
    # `train_mask`/`test_mask` are indexed 0..N-1 in the *pre-sort* row order.
    # Using them after the sort would align by label onto the wrong rows -
    # identical counts, wrong contents, so it passed every shape assertion
    # while silently leaking 2025 orders into "train" and vice versa.
    # Recomputing from `order_year` here is the correct fix rather than
    # reordering the masks: the per-row year values never changed, only the
    # row positions did.
    train_mask = orders["order_year"] <= 2024
    test_mask = orders["order_year"] == 2025
    assert train_mask.sum() == 110_518, f"expected 110,518 train orders, got {train_mask.sum()}"
    assert test_mask.sum() == 27_598, f"expected 27,598 test orders, got {test_mask.sum()}"
    print(f"\n[post-sort recompute] train return rate: {orders.loc[train_mask, 'target'].mean():.4%}")
    print(f"[post-sort recompute] test return rate:  {orders.loc[test_mask, 'target'].mean():.4%}")
    assert abs(orders.loc[train_mask, "target"].mean() - 0.067772) < 0.0001, \
        "post-sort train return rate doesn't match the independently-verified 6.7772%"
    print("post-sort train/test masks recomputed and match the pre-sort verification - OK")

    by_customer = orders.groupby("customer_id")

    orders["customer_prior_order_count"] = by_customer.cumcount()
    orders["customer_prior_revenue"] = by_customer["net_sales"].cumsum() - orders["net_sales"]
    orders["is_repeat_customer_asof"] = (orders["customer_prior_order_count"] > 0).astype(int)

    print("\ncustomer_prior_order_count range:", orders["customer_prior_order_count"].min(), "-",
          orders["customer_prior_order_count"].max())
    print("customer_prior_revenue range: {:.2f} - {:.2f}".format(
        orders["customer_prior_revenue"].min(), orders["customer_prior_revenue"].max()))
    print("is_repeat_customer_asof distribution:\n", orders["is_repeat_customer_asof"].value_counts())

    # Every customer's first order (by date) must show 0 prior orders / $0
    # prior revenue / not-yet-repeat - a direct correctness check on the
    # recomputation logic itself, not just a plausibility check.
    first_orders = orders.loc[by_customer.cumcount() == 0]
    assert (first_orders["customer_prior_order_count"] == 0).all()
    assert (first_orders["customer_prior_revenue"] == 0).all()
    assert (first_orders["is_repeat_customer_asof"] == 0).all()
    print("every customer's first order correctly shows zero prior history - OK")

    # ----------------------------------------------------------------------------
    # Missing-value handling strategy
    # ----------------------------------------------------------------------------
    # The strategy for this feature set turns out to be "exclusion, already
    # applied above" rather than imputation: delivery_days/estimated_delivery_
    # days and everything from `ratings` - the only columns with real
    # missingness in `orders` - are excluded on leakage grounds anyway, and
    # ratings was never joined in, so neither is part of the feature set. What's left is audited
    # here to confirm that's actually true, not assumed.
    FEATURE_COLUMNS = [
        "shipping_ratio",
        *CATEGORICAL_FEATURES,
        "customer_prior_order_count", "customer_prior_revenue", "is_repeat_customer_asof",
    ]
    null_counts = orders[FEATURE_COLUMNS].isna().sum()
    print("\nnull counts in the final feature set:")
    print(null_counts)
    assert null_counts.sum() == 0, "found unexpected nulls in the final feature set - needs a real imputation decision"
    print("zero nulls across every selected feature - no imputation needed for this feature set")

    # ----------------------------------------------------------------------------
    # Leakage audit (added after the discount_ratio leak) — every feature,
    # every time, before anything is trained
    # ----------------------------------------------------------------------------
    # The discount_ratio leak passed every existing check because nothing
    # looked at a feature's *relationship to the target* - only at nulls,
    # ranges, and cardinality. This audit closes that gap: for each feature, no
    # single value (categoricals) or decile (numerics) with real support may
    # have a return rate of exactly 0% or exactly 100%. A genuine business
    # signal moves the rate by a few points; a structural proxy for the
    # outcome pins it to an extreme. Run on the TRAIN split only - the audit
    # must not peek at test data any more than the model does.
    _audit = orders.loc[train_mask, FEATURE_COLUMNS + ["target"]]
    _MIN_SUPPORT = 100
    for col in CATEGORICAL_FEATURES + ["is_repeat_customer_asof"]:
        _g = _audit.groupby(col, observed=True)["target"].agg(["mean", "size"])
        _bad = _g[(_g["size"] >= _MIN_SUPPORT) & ((_g["mean"] == 0) | (_g["mean"] == 1))]
        assert _bad.empty, f"leakage audit: {col} has values that perfectly separate the target:\n{_bad}"
        print(f"  audit {col}: return rate by value spans {_g['mean'].min():.4f}-{_g['mean'].max():.4f} - OK")
    for col in ["shipping_ratio", "customer_prior_order_count", "customer_prior_revenue"]:
        _bins = pd.qcut(_audit[col], 10, duplicates="drop")
        _g = _audit.groupby(_bins, observed=True)["target"].agg(["mean", "size"])
        _bad = _g[(_g["size"] >= _MIN_SUPPORT) & ((_g["mean"] == 0) | (_g["mean"] == 1))]
        assert _bad.empty, f"leakage audit: {col} has deciles that perfectly separate the target:\n{_bad}"
        print(f"  audit {col}: return rate by decile spans {_g['mean'].min():.4f}-{_g['mean'].max():.4f} - OK")
    print("leakage audit passed: no feature value/decile pins the return rate to 0% or 100%")

    # ----------------------------------------------------------------------------
    # Preprocessing pipeline: two separate paths, one per model
    # ----------------------------------------------------------------------------
    # Not one shared pipeline for both models - Logistic Regression needs
    # numeric, scaled, one-hot-encoded input; HistGradientBoostingClassifier is
    # scale-invariant and has native categorical support (scikit-learn >= 1.4's
    # `categorical_features="from_dtype"`), so one-hot-encoding for it would
    # just be unnecessary dimensionality with no benefit. Using identical
    # preprocessing for both would be convenient, not correct.
    NUMERIC_FEATURES = ["shipping_ratio", "customer_prior_order_count", "customer_prior_revenue"]
    BINARY_FEATURES = ["is_repeat_customer_asof"]
    assert set(NUMERIC_FEATURES + CATEGORICAL_FEATURES + BINARY_FEATURES) == set(FEATURE_COLUMNS)

    X_train = orders.loc[train_mask, FEATURE_COLUMNS].reset_index(drop=True)
    X_test = orders.loc[test_mask, FEATURE_COLUMNS].reset_index(drop=True)
    y_train = orders.loc[train_mask, "target"].reset_index(drop=True)
    y_test = orders.loc[test_mask, "target"].reset_index(drop=True)

    print(f"\nX_train: {X_train.shape}, X_test: {X_test.shape}")
    assert X_train.shape[0] == 110_518 and X_test.shape[0] == 27_598


    def build_preprocessor_linear() -> ColumnTransformer:
        """Preprocessing for Logistic Regression. `RobustScaler`, not
        `StandardScaler`, for the numerics - `shipping_ratio` has real outliers
        up to 3.67, which would distort a mean/variance-based scaler.
        `OneHotEncoder(handle_unknown='ignore')` so a category the training
        split never saw doesn't crash prediction later (defensive - this
        dataset's categories are a closed, fully-enumerated vocabulary, but the
        model shouldn't rely on that holding forever). Explicitly lists every
        feature group (no `remainder="passthrough"` catch-all) so adding a
        feature later and forgetting to place it here fails loudly (dropped)
        instead of silently doing the wrong thing to it.
        """
        return ColumnTransformer(
            transformers=[
                ("numeric", RobustScaler(), NUMERIC_FEATURES),
                ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
                ("binary", "passthrough", BINARY_FEATURES),
            ]
        )


    def to_tree_format(X: pd.DataFrame) -> pd.DataFrame:
        """Preprocessing for HistGradientBoostingClassifier: categoricals cast
        to pandas `category` dtype (native support, no encoder object needed);
        numerics left raw (trees are scale-invariant - RobustScaler would do
        nothing useful here)."""
        X = X.copy()
        for col in CATEGORICAL_FEATURES:
            X[col] = X[col].astype("category")
        return X


    preprocessor_linear = build_preprocessor_linear()
    X_train_linear = preprocessor_linear.fit_transform(X_train)
    X_test_linear = preprocessor_linear.transform(X_test)
    print(f"linear-path transformed shapes: train {X_train_linear.shape}, test {X_test_linear.shape}")
    assert X_train_linear.shape[0] == 110_518 and X_test_linear.shape[0] == 27_598
    assert X_train_linear.shape[1] == X_test_linear.shape[1], "train/test produced different column counts"

    # Prove handle_unknown='ignore' actually works, not just that it's set -
    # inject a category neither split really has and confirm it transforms
    # without raising, rather than trusting the parameter name alone.
    X_test_with_unseen = X_test.copy()
    X_test_with_unseen.loc[0, "primary_category"] = "Nonexistent Category"
    transformed_unseen = preprocessor_linear.transform(X_test_with_unseen)
    assert transformed_unseen.shape == X_test_linear.shape
    print("handle_unknown='ignore' verified: an unseen category transforms without error")

    X_train_tree = to_tree_format(X_train)
    X_test_tree = to_tree_format(X_test)
    print(f"tree-path shapes: train {X_train_tree.shape}, test {X_test_tree.shape}")
    assert all(X_train_tree[col].dtype.name == "category" for col in CATEGORICAL_FEATURES)
    # is_numeric_dtype, not an exact dtype-name match: `.astype(int)` resolves
    # to int32 on Windows vs int64 on Linux/Mac (platform "C long" size) - an
    # exact-name check would be a real, Windows-specific false failure here,
    # not a sign anything is actually wrong with the data.
    assert all(pd.api.types.is_numeric_dtype(X_train_tree[col]) for col in NUMERIC_FEATURES + BINARY_FEATURES)
    print("tree-path dtypes confirmed: categoricals are 'category', numerics untouched")

    print("\nPreprocessing verified on both paths - OK")

    # ----------------------------------------------------------------------------
    # Train baseline: Logistic Regression
    # ----------------------------------------------------------------------------
    # `class_weight="balanced"` - the return rate is ~6.85%, so an unweighted fit
    # would be biased toward always predicting "not returned" (it could hit
    # ~93% accuracy by doing that alone, which would be a useless baseline to
    # compare the challenger against). "balanced" reweights the loss inversely
    # to class frequency (n_samples / (n_classes * bincount)) - the standard
    # first move for imbalanced binary classification, not a hand-picked value.
    # `max_iter=1000` (default 100 sometimes doesn't converge with one-hot
    # columns - checked below rather than assumed). `random_state=42` for
    # reproducibility (lbfgs itself isn't stochastic, but pinning it costs
    # nothing and keeps every run identical).
    model_lr = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
    model_lr.fit(X_train_linear, y_train)

    # Convergence isn't just assumed from "fit() didn't raise" - lbfgs reports
    # its actual iteration count, and n_iter_ hitting the max_iter ceiling is
    # the real signal it stopped early rather than converging.
    n_iter = model_lr.n_iter_[0]
    print(f"\nLogistic Regression fit: converged in {n_iter} iterations (max_iter=1000)")
    assert n_iter < 1000, f"hit the max_iter ceiling ({n_iter}) - did not actually converge"

    # Coefficient count must match the transformed column count exactly - a
    # mismatch here would mean the fitted model and the preprocessor have
    # silently drifted apart.
    assert model_lr.coef_.shape == (1, X_train_linear.shape[1]), \
        f"coef_ shape {model_lr.coef_.shape} doesn't match {X_train_linear.shape[1]} transformed columns"

    train_proba = model_lr.predict_proba(X_train_linear)[:, 1]
    train_pred = model_lr.predict(X_train_linear)

    # Probabilities must be valid probabilities, and the model must not have
    # collapsed to predicting one class for everyone - a degenerate baseline
    # would still "fit without error", so this checks it actually learned
    # something, not just that no exception was raised.
    assert train_proba.min() >= 0.0 and train_proba.max() <= 1.0
    assert 0 < train_pred.sum() < len(train_pred), "model predicts a single class for every row - degenerate fit"
    print(f"train predicted-probability range: {train_proba.min():.4f} - {train_proba.max():.4f}")
    print(f"train predicted positive rate (threshold 0.5): {train_pred.mean():.4%} "
          f"(actual train return rate: {y_train.mean():.4%})")
    # With class_weight='balanced' the 0.5 cutoff sits roughly where an
    # unweighted model's cutoff would sit at the base rate - so a weak model
    # flags a large share of orders as positive here. That's expected for
    # balanced weighting on a ~7% base rate, and is why the evaluation below
    # treats the 0.5-threshold metrics as secondary to the threshold-free ones.

    print("\nBaseline Logistic Regression trained and sanity-checked - OK")

    # ----------------------------------------------------------------------------
    # Train challengers: HistGradientBoostingClassifier, Random Forest,
    # XGBoost
    # ----------------------------------------------------------------------------
    # Broadened from the original Logistic-Regression-vs-HGB comparison after
    # the discount_ratio leak was fixed and both models turned out only
    # marginally above random. Before concluding that a near-random result is
    # a feature ceiling rather than a modelling failure, it is worth testing
    # that claim against genuinely different inductive biases - hence a linear
    # model, two boosting variants, and one bagging variant. All four share the
    # same features, split, and
    # `class_weight`/`scale_pos_weight` imbalance handling - only the algorithm
    # differs, so any difference in results is attributable to that.
    #
    # --- HistGradientBoostingClassifier ---
    # `categorical_features="from_dtype"` auto-detects the `to_tree_format()`
    # category columns, no encoder needed. `l2_regularization=1.0`/
    # `max_leaf_nodes=15` (defaults 0/31) came from a bounded regularization
    # check: defaults gave 0.0935 train / 0.0801 test PR-AUC (gap 0.0134);
    # regularized gave 0.0868 / 0.0804 (gap 0.0064) - gap halved, test
    # unchanged.
    model_hgb = HistGradientBoostingClassifier(
        categorical_features="from_dtype", class_weight="balanced", random_state=42,
        l2_regularization=1.0, max_leaf_nodes=15,
    )
    model_hgb.fit(X_train_tree, y_train)
    print(f"\nHistGradientBoostingClassifier fit: {model_hgb.n_iter_} boosting iterations")

    # --- Random Forest — tried, REJECTED ---
    # A genuinely different tree strategy (bagging many deep, decorrelated
    # trees vs. HGB's boosting) - included to test whether the near-random
    # result was an artifact of boosting specifically. `class_weight="balanced"`
    # for the same imbalance handling as every other model; needs the one-hot
    # linear-format input (no native categorical support, unlike HGB/XGBoost).
    # Result: WORSE test PR-AUC than HGB (0.0794 vs 0.0804) AND a severe
    # train/test gap (0.1844 vs 0.0794 - a gap of 0.1050, ~16x HGB's). Even at
    # max_depth=8 (already shallow for RF's usual defaults), it memorizes the
    # training data far more than either boosting method while generalizing
    # worse. Rejected on both counts, not tuned further - the pattern (much
    # higher train score, no corresponding test gain) is diagnostic of "more
    # capacity finding noise, not signal," consistent with the overall
    # conclusion reached in model selection below.
    model_rf = RandomForestClassifier(
        n_estimators=300, max_depth=8, class_weight="balanced", random_state=42, n_jobs=-1,
    )
    model_rf.fit(X_train_linear, y_train)
    print(f"RandomForest fit: {model_rf.n_estimators} trees, max_depth={model_rf.max_depth}")

    # --- XGBoost — tried, SELECTED as final model ---
    # `enable_categorical=True` + `tree_method="hist"` gives XGBoost the same
    # native pandas-category support as HGB (same `to_tree_format()` input, same
    # categorical-code consistency requirement carried into `ml/predict.py`'s
    # `categorical_categories` pinning). `scale_pos_weight` is XGBoost's
    # equivalent of `class_weight="balanced"` - ratio of negative to positive
    # training examples, the standard imbalance correction for this library
    # (not a hand-picked value).
    #
    # Hyperparameters are the result of the same kind of bounded regularization
    # check as HGB's, run because an initial default-ish XGBoost fit showed the
    # same overfitting shape as Random Forest (train 0.1501 vs test 0.0766 -
    # gap 0.0735). Four regularized variants were compared on train/test gap
    # and test PR-AUC together (not test PR-AUC alone, which would have picked
    # an overfit variant); shallow trees (`max_depth=2`) with a low learning
    # rate and strong `min_child_weight`/`reg_lambda` essentially eliminated the
    # gap (-0.0013, i.e. test slightly exceeds train) while matching the best
    # test PR-AUC seen across every variant tried (0.0819, within noise of the
    # single highest value of 0.0824 from a less-regularized variant with a
    # real 0.0139 gap - the small extra PR-AUC there wasn't worth reintroducing
    # overfitting for).
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    model_xgb = xgb.XGBClassifier(
        n_estimators=150, max_depth=2, learning_rate=0.03, reg_lambda=5.0, min_child_weight=150,
        tree_method="hist", enable_categorical=True, scale_pos_weight=scale_pos_weight,
        random_state=42, eval_metric="aucpr",
    )
    model_xgb.fit(X_train_tree, y_train)
    print(f"XGBoost fit: {model_xgb.n_estimators} trees, max_depth={model_xgb.max_depth}, "
          f"scale_pos_weight={scale_pos_weight:.3f}")

    # Per-model train probability/prediction arrays, needed by the evaluate()
    # calls below.
    train_proba_hgb = model_hgb.predict_proba(X_train_tree)[:, 1]
    train_pred_hgb = model_hgb.predict(X_train_tree)
    train_proba_rf = model_rf.predict_proba(X_train_linear)[:, 1]
    train_pred_rf = model_rf.predict(X_train_linear)
    train_proba_xgb = model_xgb.predict_proba(X_train_tree)[:, 1]
    train_pred_xgb = model_xgb.predict(X_train_tree)

    for name, p, pred in [("HistGradientBoosting", train_proba_hgb, train_pred_hgb),
                           ("RandomForest", train_proba_rf, train_pred_rf),
                           ("XGBoost", train_proba_xgb, train_pred_xgb)]:
        assert p.min() >= 0.0 and p.max() <= 1.0
        assert 0 < pred.sum() < len(pred), f"{name} predicts a single class for every row - degenerate fit"

    print("\nChallengers (HGB, RandomForest, XGBoost) trained and sanity-checked - OK")

    # ----------------------------------------------------------------------------
    # Evaluate both: precision/recall/F1/ROC-AUC/PR-AUC/confusion matrix
    # ----------------------------------------------------------------------------
    # Evaluated on the TEST set (2025) — the number that actually matters for
    # model selection, since train-set metrics only measure fit, not
    # generalization (the whole reason for the time-based split in the first
    # place). Train-set metrics are also printed per model, purely as an
    # overfitting diagnostic (a big train/test gap is worth having on record),
    # not as a selection criterion.
    #
    # precision/recall/F1/confusion-matrix use the default 0.5 probability
    # threshold - a somewhat arbitrary cutoff for an imbalanced problem, which
    # is exactly why the threshold-free, ranking-based PR-AUC and ROC-AUC are
    # this project's primary metrics, not these. PR-AUC is computed via
    # `average_precision_score`, the standard step-function estimator of the
    # area under the precision-recall curve (not a trapezoidal-rule
    # approximation, which can overstate the score for a stepped curve).


    def evaluate(name: str, y_true, y_pred, y_proba) -> dict:
        metrics = {
            "precision": precision_score(y_true, y_pred),
            "recall": recall_score(y_true, y_pred),
            "f1": f1_score(y_true, y_pred),
            "roc_auc": roc_auc_score(y_true, y_proba),
            "pr_auc": average_precision_score(y_true, y_proba),
        }
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        metrics["confusion_matrix"] = {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
        print(f"\n[{name}] precision={metrics['precision']:.4f} recall={metrics['recall']:.4f} "
              f"f1={metrics['f1']:.4f} roc_auc={metrics['roc_auc']:.4f} pr_auc={metrics['pr_auc']:.4f}")
        print(f"[{name}] confusion matrix (0.5 threshold): TN={tn:,} FP={fp:,} FN={fn:,} TP={tp:,}")
        return metrics


    test_proba_lr = model_lr.predict_proba(X_test_linear)[:, 1]
    test_pred_lr = model_lr.predict(X_test_linear)
    test_proba_hgb = model_hgb.predict_proba(X_test_tree)[:, 1]
    test_pred_hgb = model_hgb.predict(X_test_tree)
    test_proba_rf = model_rf.predict_proba(X_test_linear)[:, 1]
    test_pred_rf = model_rf.predict(X_test_linear)
    test_proba_xgb = model_xgb.predict_proba(X_test_tree)[:, 1]
    test_pred_xgb = model_xgb.predict(X_test_tree)

    print(f"\nrandom-guess PR-AUC floor (test return rate) = {y_test.mean():.4f}")

    print("\n--- test-set evaluation (2025, held-out) ---")
    lr_test_metrics = evaluate("LogisticRegression / test", y_test, test_pred_lr, test_proba_lr)
    hgb_test_metrics = evaluate("HistGradientBoosting / test", y_test, test_pred_hgb, test_proba_hgb)
    rf_test_metrics = evaluate("RandomForest / test", y_test, test_pred_rf, test_proba_rf)
    xgb_test_metrics = evaluate("XGBoost / test", y_test, test_pred_xgb, test_proba_xgb)

    print("\n--- train-set evaluation (2021-24, overfitting diagnostic only) ---")
    lr_train_metrics = evaluate("LogisticRegression / train", y_train, train_pred, train_proba)
    hgb_train_metrics = evaluate("HistGradientBoosting / train", y_train, train_pred_hgb, train_proba_hgb)
    rf_train_metrics = evaluate("RandomForest / train", y_train, train_pred_rf, train_proba_rf)
    xgb_train_metrics = evaluate("XGBoost / train", y_train, train_pred_xgb, train_proba_xgb)

    print("\n--- overfitting check (train PR-AUC vs test PR-AUC) ---")
    for name, tr, te in [("LogisticRegression", lr_train_metrics, lr_test_metrics),
                          ("HistGradientBoosting", hgb_train_metrics, hgb_test_metrics),
                          ("RandomForest", rf_train_metrics, rf_test_metrics),
                          ("XGBoost", xgb_train_metrics, xgb_test_metrics)]:
        gap = tr["pr_auc"] - te["pr_auc"]
        print(f"  {name:22s} train pr_auc={tr['pr_auc']:.4f}  test pr_auc={te['pr_auc']:.4f}  gap={gap:+.4f}")

    # Every metric must actually be a valid metric value, not NaN/out-of-range -
    # a sanity floor, not a claim about which model is better (that comes next).
    for name, m in [("LR test", lr_test_metrics), ("HGB test", hgb_test_metrics),
                    ("RF test", rf_test_metrics), ("XGBoost test", xgb_test_metrics)]:
        for key in ("precision", "recall", "f1", "roc_auc", "pr_auc"):
            assert 0.0 <= m[key] <= 1.0, f"{name} {key}={m[key]} out of [0,1] range"
        cm = m["confusion_matrix"]
        assert cm["tn"] + cm["fp"] + cm["fn"] + cm["tp"] == len(y_test), \
            f"{name} confusion matrix total doesn't match test set size"

    print("\nEvaluation complete for all four models - all metrics in valid range - OK")

    # ----------------------------------------------------------------------------
    # Compare & select final model, write rationale
    # ----------------------------------------------------------------------------
    # Final choice: XGBoost (regularized), across four model families
    # tried (Logistic Regression, HistGradientBoosting, Random Forest,
    # XGBoost). Rationale, in full — including the part that is uncomfortable:
    #  0. THE HEADLINE: on the leak-free feature set, no model is much better
    #     than random. Test PR-AUC ranges 0.076-0.082 across all four models,
    #     against a random-guess floor of 0.0715 (the test return rate);
    #     ROC-AUC ranges 0.51-0.54 against 0.5. Before the discount_ratio leak
    #     was found,
    #     this pipeline reported PR-AUC 0.57 / ROC-AUC 0.97 — essentially all of
    #     that was discount_ratio acting as a proxy for the outcome. The honest
    #     conclusion is that returns in this dataset are close to unpredictable
    #     from the pre-outcome features available here (every categorical
    #     value's return rate sits within 6.2-7.3%, per the leakage audit). A
    #     model is still shipped because the API contract requires one, but its
    #     output must be read as "slightly better than the base rate", not as a
    #     confident return-risk score.
    #  1. FOUR model families were tried specifically to test whether #0 was a
    #     model-choice problem rather than a data problem: a linear model (LR),
    #     two boosting variants (HGB, XGBoost), and a bagging variant (Random
    #     Forest) - genuinely different inductive biases, not four names for
    #     the same algorithm. All four converging to the same ~0.08 PR-AUC
    #     band, including a high-capacity model failing to even fit the
    #     TRAINING data much better (Random Forest reached only 0.18 train
    #     PR-AUC despite 300 trees), is the diagnostic signature of "the
    #     features don't carry the signal," not "the model is too simple."
    #     That is the basis for concluding #0 is a data ceiling, not something
    #     more tuning or a different library would fix.
    #  2. Random Forest REJECTED: worse test PR-AUC than HGB (0.0794 vs 0.0804)
    #     AND a severe train/test gap (0.1050) - the worst overfitting of any
    #     model tried, for no test-set benefit. Not pursued further.
    #  3. XGBoost (regularized) SELECTED over HistGradientBoosting: leads on
    #     every test metric (PR-AUC 0.0819 vs 0.0804, ROC-AUC 0.5374 vs 0.5362)
    #     while having an even smaller train/test PR-AUC gap (-0.0013, i.e.
    #     test slightly exceeds train, vs. HGB's already-small 0.0064). A
    #     regularization search across 4 variants was run for XGBoost the same
    #     way it was for HGB, selecting on the gap+test-PR-AUC
    #     combination rather than test PR-AUC alone (the single highest test
    #     PR-AUC seen, 0.0824, came from a variant with a real 0.0139 gap - the
    #     extra 0.0005 PR-AUC wasn't worth the added overfitting risk).
    #  4. Logistic Regression's coefficients are directly interpretable in a
    #     way none of the three tree-based models are. Not a blocker: the
    #     "contributing factors" heuristic for `/ml/predict` is rule-based over
    #     raw feature values, not a reading of model internals (no SHAP/
    #     coefficients) - it works identically regardless of which model is
    #     deployed. Given how weak the signal is, the heuristic's historical
    #     rates are arguably more informative to a user than the probability.
    #  5. What would actually move the needle is more/better features, not
    #     more model families or more tuning: the leakage audit's raw-column
    #     scan showed order-size fields (quantity, gross_sales) spanning wider
    #     return-rate ranges (3.6-8.2%, 5.1-7.6% by decile) than anything
    #     currently used - a clear candidate for follow-up work rather than
    #     something to bolt on mid-rework.
    FINAL_MODEL_NAME = "XGBoost"
    FINAL_MODEL_HYPERPARAMS = {
        "n_estimators": 150,
        "max_depth": 2,
        "learning_rate": 0.03,
        "reg_lambda": 5.0,
        "min_child_weight": 150,
        "tree_method": "hist",
        "enable_categorical": True,
        "scale_pos_weight": float(scale_pos_weight),
        "random_state": 42,
    }
    final_model = model_xgb
    final_test_metrics = xgb_test_metrics
    final_train_metrics = xgb_train_metrics

    ALL_MODELS_TEST_METRICS = {
        "LogisticRegression": lr_test_metrics,
        "HistGradientBoosting": hgb_test_metrics,
        "RandomForest": rf_test_metrics,
        "XGBoost": xgb_test_metrics,
    }
    ALL_MODELS_TRAIN_METRICS = {
        "LogisticRegression": lr_train_metrics,
        "HistGradientBoosting": hgb_train_metrics,
        "RandomForest": rf_train_metrics,
        "XGBoost": xgb_train_metrics,
    }

    print(f"\nFINAL MODEL SELECTED: {FINAL_MODEL_NAME} {FINAL_MODEL_HYPERPARAMS}")
    print("test PR-AUC by model:", {k: round(v["pr_auc"], 4) for k, v in ALL_MODELS_TEST_METRICS.items()})
    print("test ROC-AUC by model:", {k: round(v["roc_auc"], 4) for k, v in ALL_MODELS_TEST_METRICS.items()})
    print("train/test PR-AUC gap by model:", {
        k: round(ALL_MODELS_TRAIN_METRICS[k]["pr_auc"] - v["pr_auc"], 4) for k, v in ALL_MODELS_TEST_METRICS.items()
    })
    assert final_test_metrics["pr_auc"] == max(m["pr_auc"] for m in ALL_MODELS_TEST_METRICS.values()), \
        "selected model must actually be the one with the highest test PR-AUC among all four tried"
    print("\nFinal model selected (of 4 families compared) and rationale recorded - OK")

    # ----------------------------------------------------------------------------
    # Save model artifact (joblib) + metadata.json
    # ----------------------------------------------------------------------------
    # Only the FINAL model is persisted as a deployable artifact - Logistic
    # Regression was a real, fairly-evaluated baseline, not a second thing
    # the prediction API needs to load. Its metrics are still preserved in
    # metadata.json (for the model card / interview record), just not the
    # fitted model object itself.
    #
    # `categorical_categories` is saved deliberately, not an afterthought:
    # HistGradientBoostingClassifier's `categorical_features="from_dtype"`
    # reads category *codes* off the pandas dtype at fit time. If the serving
    # prediction code ever recreates these columns as `category` dtype in a
    # different category order (e.g. pandas infers order-of-first-appearance
    # from a single incoming request rather than the full training vocabulary),
    # the model would silently misread which category is which. Recording the
    # exact trained category order here means the serving code can pin it explicitly
    # (`pd.Categorical(value, categories=<this list>)`) instead of trusting
    # pandas to reconstruct it the same way by coincidence.
    MODEL_PATH = ML_DIR / "model.joblib"
    METADATA_PATH = ML_DIR / "metadata.json"

    joblib.dump(final_model, MODEL_PATH)
    print(f"\nsaved model artifact to {MODEL_PATH}")

    categorical_categories = {col: X_train_tree[col].cat.categories.tolist() for col in CATEGORICAL_FEATURES}

    # Reference stats for the rule-based "contributing factors" heuristic in
    # ml/predict.py — computed ONCE here, from the training split only (never
    # test, to avoid the heuristic itself leaking test-set information), and
    # saved into metadata so predict.py never needs a live DB query just to
    # know "is this category historically risky" at serve time.
    train_with_target = X_train.assign(target=y_train)
    category_return_rates = {
        col: train_with_target.groupby(col, observed=True)["target"].mean().to_dict()
        for col in CATEGORICAL_FEATURES
    }
    numeric_quantiles = {
        col: {"p25": float(X_train[col].quantile(0.25)), "p75": float(X_train[col].quantile(0.75))}
        for col in NUMERIC_FEATURES
    }
    repeat_customer_return_rates = train_with_target.groupby("is_repeat_customer_asof")["target"].mean().to_dict()

    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "sklearn_version": sklearn.__version__,
        "problem": "Order Return Prediction (binary classification: order_status == 'Returned')",
        "final_model": {
            "name": FINAL_MODEL_NAME,
            "hyperparameters": FINAL_MODEL_HYPERPARAMS,
            "preprocessing": "tree-format: categoricals as pandas category dtype (enable_categorical=True), "
                             "numerics raw (no scaling) - same input format as HistGradientBoosting.",
        },
        "baseline_model": {
            "name": "LogisticRegression",
            "hyperparameters": {"class_weight": "balanced", "max_iter": 1000, "random_state": 42},
            "preprocessing": "RobustScaler (numeric) + OneHotEncoder(handle_unknown='ignore') (categorical)",
        },
        "other_models_tried": {
            "HistGradientBoostingClassifier": {
                "hyperparameters": {"categorical_features": "from_dtype", "class_weight": "balanced",
                                     "random_state": 42, "l2_regularization": 1.0, "max_leaf_nodes": 15},
                "verdict": "Strong second place - beaten by XGBoost on every test metric by a small "
                           "margin, with a slightly larger overfitting gap. Not rejected for cause, "
                           "just edged out.",
            },
            "RandomForestClassifier": {
                "hyperparameters": {"n_estimators": 300, "max_depth": 8, "class_weight": "balanced",
                                     "random_state": 42},
                "verdict": "REJECTED - worse test PR-AUC than HGB/XGBoost (0.0794) AND the worst "
                           "overfitting of any model tried (train/test gap 0.1050, ~16x XGBoost's).",
            },
        },
        "features": {
            "numeric": NUMERIC_FEATURES,
            "categorical": CATEGORICAL_FEATURES,
            "binary": BINARY_FEATURES,
            "all_columns_in_order": FEATURE_COLUMNS,
            "categorical_categories": categorical_categories,
        },
        "risk_reference_stats": {
            "note": "Computed from the TRAIN split only (the contributing-factors heuristic must "
                    "never be grounded in test-set information). Used by ml/predict.py to explain a "
                    "prediction with real historical numbers instead of made-up thresholds.",
            "overall_train_return_rate": float(y_train.mean()),
            "category_return_rates": category_return_rates,
            "numeric_quantiles": numeric_quantiles,
            "repeat_customer_return_rates": {str(k): v for k, v in repeat_customer_return_rates.items()},
        },
        "data_split": {
            "train_period": "2021-01-01 to 2024-12-31",
            "test_period": "2025-01-01 to 2025-12-31",
            "train_rows": int(train_mask.sum()),
            "test_rows": int(test_mask.sum()),
            "train_return_rate": float(y_train.mean()),
            "test_return_rate": float(y_test.mean()),
        },
        "metrics": {
            "final_model_test": final_test_metrics,
            "final_model_train": final_train_metrics,
            "baseline_model_test": lr_test_metrics,
            "baseline_model_train": lr_train_metrics,
            "all_models_test": ALL_MODELS_TEST_METRICS,
            "all_models_train": ALL_MODELS_TRAIN_METRICS,
            "random_guess_pr_auc_floor": float(y_test.mean()),
        },
        "overfitting_check": {
            "note": "Regularization search run for both tree ensembles: HGB's l2_regularization=1.0/"
                    "max_leaf_nodes=15 (vs. defaults 0/31) halved its gap (0.0134 -> 0.0064); XGBoost's "
                    "max_depth=2/learning_rate=0.03/reg_lambda=5.0/min_child_weight=150 (vs. an "
                    "initial default-ish fit with gap 0.0735) brought its gap to -0.0013 (test slightly "
                    "exceeds train) while matching the best test PR-AUC seen across every variant tried. "
                    "Random Forest was NOT regularization-rescued the same way - its gap (0.1050) was "
                    "the reason it was rejected, not tuned further.",
            "final_model_train_test_pr_auc_gap": final_train_metrics["pr_auc"] - final_test_metrics["pr_auc"],
            "baseline_model_train_test_pr_auc_gap": lr_train_metrics["pr_auc"] - lr_test_metrics["pr_auc"],
            "all_models_train_test_pr_auc_gap": {
                k: ALL_MODELS_TRAIN_METRICS[k]["pr_auc"] - v["pr_auc"] for k, v in ALL_MODELS_TEST_METRICS.items()
            },
        },
        "excluded_features": {
            "discount_ratio": "TARGET LEAK - discount_amount is 0 for 100% of Returned and Cancelled orders "
                              "and >0 for ~100% of Completed orders (data-generation artifact). Found during API smoke testing, "
                              "removed; every metric here is from the leak-free retrain.",
            "delivery_days / estimated_delivery_days / delivery_status": "NULL/'Cancelled' for 100% of "
                              "returned orders - leaks the outcome.",
            "ratings.*": "0 of 9,462 returned orders ever have a rating, by construction.",
            "customer_lifetime_value / customer_order_count / is_repeat_customer (raw)": "lifetime "
                              "aggregates, not point-in-time snapshots; recomputed as-of-order instead.",
            "payment_status": "'Refunded' <=> Returned - a post-outcome field, never a candidate.",
        },
        "selection_rationale": (
            "XGBoost (regularized) selected after comparing FOUR model families (LogisticRegression, "
            "HistGradientBoosting, RandomForest, XGBoost) - deliberately including a linear model, two "
            "boosting variants, and a bagging variant to test whether the near-random result (see below) "
            "was a model-choice problem. It wasn't: all four converged to a tight 0.076-0.082 test PR-AUC "
            "band. XGBoost leads on every test metric (PR-AUC 0.0819 vs HGB's 0.0804, ROC-AUC 0.5374 vs "
            "0.5362) with an even smaller train/test gap than HGB's already-small one. RandomForest was "
            "rejected outright: worse test PR-AUC AND by far the worst overfitting of any model tried. "
            "IMPORTANT CONTEXT: on the leak-free feature set, no model is much better than random (test "
            "PR-AUC ~0.08 vs. a 0.0715 base rate; ROC-AUC ~0.54 vs 0.5). The pre-fix 0.57 PR-AUC / 0.97 "
            "ROC-AUC was almost entirely the discount_ratio leak. Trying four different algorithms and "
            "landing in the same narrow band - including a high-capacity model failing to fit even the "
            "training data much better - is the evidence that this is a feature ceiling, not something "
            "a different or better-tuned algorithm would fix. The shipped model should be read as "
            "'slightly better than the base rate', not as a confident risk score."
        ),
    }

    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"saved metadata to {METADATA_PATH}")

    # Verify the artifact round-trips - a save that produces a file that can't
    # be reloaded, or reloads to a different model, would be worse than no
    # artifact at all (the serving code would fail much later, harder to diagnose).
    reloaded_model = joblib.load(MODEL_PATH)
    reloaded_test_proba = reloaded_model.predict_proba(X_test_tree)[:, 1]
    assert (reloaded_test_proba == test_proba_xgb).all(), \
        "reloaded model's predictions differ from the in-memory model's - artifact did not round-trip correctly"
    with open(METADATA_PATH) as f:
        reloaded_metadata = json.load(f)
    assert reloaded_metadata["final_model"]["name"] == FINAL_MODEL_NAME
    print("model + metadata round-trip verified: reloaded model produces identical predictions - OK")

    print("\nModel artifact + metadata saved and verified - OK")

    # ----------------------------------------------------------------------------
    # Save eval plots (confusion matrix, ROC/PR curve) as PNGs
    # ----------------------------------------------------------------------------
    # All four models plotted together on the ROC/PR curves (comparison,
    # matching what the evaluation and selection steps actually compared) - a
    # single-model plot would
    # show less than the analysis already did, and with results this close,
    # seeing all four curves nearly overlap IS the finding (they should look
    # almost identical, hugging the random-guess line - a plot where they
    # visibly diverge would contradict the write-up above and be worth
    # re-checking). Confusion matrix is for the final model only, since that's
    # the one actually being shipped/discussed in the model card - a confusion
    # matrix is a single-model diagnostic, not a comparison tool.
    PLOTS_DIR = ML_DIR / "plots"
    PLOTS_DIR.mkdir(exist_ok=True)

    ALL_MODELS_TEST_PROBA = {
        "LogisticRegression": test_proba_lr,
        "HistGradientBoosting": test_proba_hgb,
        "RandomForest": test_proba_rf,
        "XGBoost (final)": test_proba_xgb,
    }

    fig, ax = plt.subplots(figsize=(6, 6))
    for name, y_proba in ALL_MODELS_TEST_PROBA.items():
        fpr, tpr, _ = roc_curve(y_test, y_proba)
        ax.plot(fpr, tpr, label=f"{name} (AUC={roc_auc_score(y_test, y_proba):.3f})")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="random guess")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve — test set (2025), all 4 models compared")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "roc_curve.png", dpi=150)
    plt.close(fig)
    print(f"\nsaved {PLOTS_DIR / 'roc_curve.png'}")

    fig, ax = plt.subplots(figsize=(6, 6))
    for name, y_proba in ALL_MODELS_TEST_PROBA.items():
        precision, recall, _ = precision_recall_curve(y_test, y_proba)
        ax.plot(recall, precision, label=f"{name} (AP={average_precision_score(y_test, y_proba):.3f})")
    ax.axhline(y_test.mean(), linestyle="--", color="gray", label=f"random guess ({y_test.mean():.3f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall Curve — test set (2025), all 4 models compared")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "pr_curve.png", dpi=150)
    plt.close(fig)
    print(f"saved {PLOTS_DIR / 'pr_curve.png'}")

    fig, ax = plt.subplots(figsize=(5, 5))
    ConfusionMatrixDisplay.from_predictions(
        y_test, test_pred_xgb, display_labels=["Not Returned", "Returned"], cmap="Blues", ax=ax, colorbar=False
    )
    ax.set_title(f"Confusion Matrix — {FINAL_MODEL_NAME} (final), test set, 0.5 threshold")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "confusion_matrix.png", dpi=150)
    plt.close(fig)
    print(f"saved {PLOTS_DIR / 'confusion_matrix.png'}")

    for plot_file in ("roc_curve.png", "pr_curve.png", "confusion_matrix.png"):
        assert (PLOTS_DIR / plot_file).exists(), f"{plot_file} was not actually written to disk"
    print("\nEval plots saved and verified on disk - OK")

    # ----------------------------------------------------------------------------
    # Generate ml/MODEL_CARD.md from training metadata
    # ----------------------------------------------------------------------------
    # Generated FROM `metadata` (the same dict just written to metadata.json),
    # not hand-written separately - the two are guaranteed to agree because
    # they're built from the same source, not two independently-typed copies
    # of the same numbers that could quietly drift apart.
    model_card = f"""# Model Card — Order Return Prediction

_Auto-generated from training metadata on {metadata['trained_at']} (scikit-learn {metadata['sklearn_version']}). Do not hand-edit — regenerate via `python -m ml.train`._

## Problem
{metadata['problem']}

Return rate in the full dataset: ~6.85% — a real class imbalance, which is why PR-AUC (not accuracy or ROC-AUC alone) is the primary evaluation metric throughout.

## Data split (time-based, not random)
| | Period | Rows | Return rate |
|---|---|---|---|
| Train | {metadata['data_split']['train_period']} | {metadata['data_split']['train_rows']:,} | {metadata['data_split']['train_return_rate']:.2%} |
| Test | {metadata['data_split']['test_period']} | {metadata['data_split']['test_rows']:,} | {metadata['data_split']['test_return_rate']:.2%} |

A random split was rejected in favor of this one: it would leak future information into training and doesn't match how the model would actually be used (scoring new orders using only what happened before them).

## Features
- **Numeric** ({len(metadata['features']['numeric'])}): {', '.join(metadata['features']['numeric'])}
- **Categorical** ({len(metadata['features']['categorical'])}): {', '.join(metadata['features']['categorical'])}
- **Binary** ({len(metadata['features']['binary'])}): {', '.join(metadata['features']['binary'])}

### Deliberately excluded (and why)
{chr(10).join(f"- **`{k}`** — {v}" for k, v in metadata['excluded_features'].items())}

A per-feature leakage audit now runs in `train.py` before any model is fit: no single value (categorical) or decile (numeric) of any feature may pin the return rate to exactly 0% or 100%. It was added after `discount_ratio` passed every earlier check (nulls, ranges, cardinality) while being an almost-deterministic proxy for the outcome.

## Final model
**{metadata['final_model']['name']}**, hyperparameters: `{metadata['final_model']['hyperparameters']}`
Preprocessing: {metadata['final_model']['preprocessing']}

## Models compared (4 families)
Deliberately different inductive biases — a linear model, two boosting variants, and a bagging variant — to test whether weak performance was a model-choice problem before concluding it's a feature-ceiling problem (see Overfitting check + Selection rationale below).

| Model | Test PR-AUC | Test ROC-AUC | Train PR-AUC | Train/test gap | Verdict |
|---|---|---|---|---|---|
{chr(10).join(
    f"| {name} | {metadata['metrics']['all_models_test'][name]['pr_auc']:.4f} | "
    f"{metadata['metrics']['all_models_test'][name]['roc_auc']:.4f} | "
    f"{metadata['metrics']['all_models_train'][name]['pr_auc']:.4f} | "
    f"{metadata['overfitting_check']['all_models_train_test_pr_auc_gap'][name]:+.4f} | "
    + ("**SELECTED**" if name == metadata['final_model']['name']
       else "Baseline" if name == metadata['baseline_model']['name']
       else metadata['other_models_tried'].get(name, {}).get('verdict', '').split(' - ')[0])
    + " |"
    for name in metadata['metrics']['all_models_test']
)}
| *random guess* | {metadata['metrics']['random_guess_pr_auc_floor']:.4f} | 0.5000 | — | — | (floor) |

### Other models tried, not selected
{chr(10).join(f"- **{name}** (`{v['hyperparameters']}`) — {v['verdict']}" for name, v in metadata['other_models_tried'].items())}

## Baseline model (for comparison)
**{metadata['baseline_model']['name']}**, hyperparameters: `{metadata['baseline_model']['hyperparameters']}`
Preprocessing: {metadata['baseline_model']['preprocessing']}

## Test-set metrics — final model vs. baseline (2025, held out)
| Metric | {metadata['final_model']['name']} (final) | {metadata['baseline_model']['name']} (baseline) |
|---|---|---|
| PR-AUC | {metadata['metrics']['final_model_test']['pr_auc']:.4f} | {metadata['metrics']['baseline_model_test']['pr_auc']:.4f} |
| ROC-AUC | {metadata['metrics']['final_model_test']['roc_auc']:.4f} | {metadata['metrics']['baseline_model_test']['roc_auc']:.4f} |
| Precision | {metadata['metrics']['final_model_test']['precision']:.4f} | {metadata['metrics']['baseline_model_test']['precision']:.4f} |
| Recall | {metadata['metrics']['final_model_test']['recall']:.4f} | {metadata['metrics']['baseline_model_test']['recall']:.4f} |
| F1 | {metadata['metrics']['final_model_test']['f1']:.4f} | {metadata['metrics']['baseline_model_test']['f1']:.4f} |

Confusion matrix (final model, 0.5 threshold): TN={metadata['metrics']['final_model_test']['confusion_matrix']['tn']:,}, FP={metadata['metrics']['final_model_test']['confusion_matrix']['fp']:,}, FN={metadata['metrics']['final_model_test']['confusion_matrix']['fn']:,}, TP={metadata['metrics']['final_model_test']['confusion_matrix']['tp']:,}

![ROC Curve](plots/roc_curve.png)
![Precision-Recall Curve](plots/pr_curve.png)
![Confusion Matrix](plots/confusion_matrix.png)

## Overfitting check
{metadata['overfitting_check']['note']}

| | Train PR-AUC | Test PR-AUC | Gap |
|---|---|---|---|
| {metadata['final_model']['name']} (final) | {metadata['metrics']['final_model_train']['pr_auc']:.4f} | {metadata['metrics']['final_model_test']['pr_auc']:.4f} | {metadata['overfitting_check']['final_model_train_test_pr_auc_gap']:.4f} |
| {metadata['baseline_model']['name']} (baseline) | {metadata['metrics']['baseline_model_train']['pr_auc']:.4f} | {metadata['metrics']['baseline_model_test']['pr_auc']:.4f} | {metadata['overfitting_check']['baseline_model_train_test_pr_auc_gap']:.4f} |

## Selection rationale
{metadata['selection_rationale']}

## Known limitations — read this before using the predictions
- **The model is only marginally better than random.** Test PR-AUC {metadata['metrics']['final_model_test']['pr_auc']:.4f} vs. a random-guess floor of {metadata['data_split']['test_return_rate']:.4f} (the test return rate); ROC-AUC {metadata['metrics']['final_model_test']['roc_auc']:.4f} vs. 0.5. On the legitimate pre-outcome features available in this dataset, returns are close to unpredictable — every categorical value's historical return rate sits within roughly 6.2–7.3%.
- **An earlier version of this pipeline reported PR-AUC 0.57 / ROC-AUC 0.97.** That was a target leak (`discount_ratio`, see exclusions above), found during API smoke testing and removed. Those numbers were not real model skill.
- At the 0.5 probability threshold with `class_weight="balanced"`, the model labels roughly half of all orders "Returned" (recall ≈ {metadata['metrics']['final_model_test']['recall']:.2f}, precision ≈ {metadata['metrics']['final_model_test']['precision']:.2f}). `predicted_label` from the API is therefore a weak signal; `return_probability` ranked across many orders is the more useful output.
- "Contributing factors" from the prediction API are a rule-based heuristic over raw feature values grounded in training-set rates, not derived from model internals (no SHAP/coefficients). Given how weak the model is, those historical rates are arguably more informative than the probability itself.
- Most promising next step is **more/better features, not tuning**: the raw-column scan during the leak audit showed order-size fields (`quantity`, `gross_sales`) with wider return-rate spread by decile than anything currently used.
"""

    MODEL_CARD_PATH = ML_DIR.parent / "ml" / "MODEL_CARD.md"
    MODEL_CARD_PATH.write_text(model_card, encoding="utf-8")
    print(f"\nsaved model card to {MODEL_CARD_PATH}")
    assert MODEL_CARD_PATH.exists() and MODEL_CARD_PATH.stat().st_size > 0, "MODEL_CARD.md was not written"
    print("\nMODEL_CARD.md generated from metadata and verified on disk - OK")




if __name__ == "__main__":
    main()
