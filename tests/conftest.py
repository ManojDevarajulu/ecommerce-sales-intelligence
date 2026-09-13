"""
tests/conftest.py — T151: shared pytest fixtures for the API test suite.

DB isolation strategy (approved 2026-09-13, see INTERVIEW_PREP.md): a
second, throwaway Postgres database — `ecommerce_test` — on the same
running container as the dev DB (docker-compose's `ecommerce_db`, host
port 5435; see docker-compose.yml). It is dropped and recreated fresh at
the start of the test session, built from the real `sql/01_schema.sql`
(so constraints/FKs/the pgvector extension are all real, not mocked), then
loaded once from a small, deterministic sample of the real CSVs under
`data/dataset/` — real SQL and real data shape, without the ~140k-row
load time of the full dataset on every test run. Rejected alternatives
(transaction-rollback-per-test, mocking the DB) are in INTERVIEW_PREP.md.

Sampling (`_load_sample_data` below): `SAMPLE_ORDERS` rows are drawn from
the main sales CSV with a fixed `random_state` (reproducible across runs),
then customers/products/order_items/ratings are all filtered down to
exactly what those sampled orders reference, so every FK resolves — no
orphaned rows, no "which customer_id do I use" guesswork in a test. A
small fixed number of extra, unreferenced customers/products are added on
top so pagination/listing tests have more than one page to work with.

Isolation is at the database level, not per-test: tests share the one
loaded dataset for the session. This matches how the app is actually used
(read-mostly analytics/ML/RAG) and keeps the fixture simple — later tests
that mutate data (e.g. the T152-154 customer CRUD tests) are expected to
use their own throwaway ids / assert non-destructively rather than rely on
per-test rollback.

Known gap: `POST /ai/reports/customer-segments` (app/api/ai.py) takes no
`db: Session = Depends(get_db)` at all — `compute_rfm_and_segments()`
reads via the app's *real* engine/SessionLocal directly (see that
endpoint's own docstring). The `client` fixture's dependency override
below does NOT redirect that one endpoint to the test DB. Not exercised
by T151-159 (no task tests it), but worth knowing before ever adding one.
"""
from collections.abc import Generator, Iterator
from pathlib import Path

import pandas as pd
import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import Settings, get_db
from app.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "dataset"
SCHEMA_SQL = PROJECT_ROOT / "sql" / "01_schema.sql"

TEST_DB_NAME = "ecommerce_test"
# Postgres always keeps a default `postgres` maintenance database alongside
# whatever POSTGRES_DB names — connecting there (never to the real
# `ecommerce` dev DB) to issue the CREATE/DROP DATABASE admin commands
# below means this fixture never opens a connection to real dev data.
_ADMIN_DB = "postgres"

# Small, deterministic sample sizes — big enough to exercise pagination,
# filters, and an FK-restricted delete; small enough to load in ~seconds.
SAMPLE_ORDERS = 300
EXTRA_CUSTOMERS = 20  # unreferenced by any sampled order — for list/pagination tests
EXTRA_PRODUCTS = 20

# Same settings resolution as the app (postgres_user/password/db + the
# `_external` host/port — see app/db/session.py's own comment on why those
# are named `_external`), used to build test-DB connection info below.
_settings = Settings()


def _pg_connect(dbname: str, *, autocommit: bool = False) -> psycopg.Connection:
    """Host-side connection (localhost:5435, matching app/db/seed.py's
    `get_conn()`) — pytest always runs on the host, never inside Docker."""
    return psycopg.connect(
        host=_settings.postgres_host_external,
        port=_settings.postgres_port_external,
        user=_settings.postgres_user,
        password=_settings.postgres_password,
        dbname=dbname,
        autocommit=autocommit,
    )


def _test_database_url() -> str:
    return (
        f"postgresql+psycopg://{_settings.postgres_user}:{_settings.postgres_password}"
        f"@{_settings.postgres_host_external}:{_settings.postgres_port_external}/{TEST_DB_NAME}"
    )


def _recreate_test_database() -> None:
    """DROP + CREATE `ecommerce_test`. `WITH (FORCE)` (PG 13+; this project
    runs pg16) disconnects any leftover session from a prior interrupted
    run instead of DROP DATABASE failing with "database is being accessed
    by other users"."""
    with _pg_connect(_ADMIN_DB, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME} WITH (FORCE)")
        conn.execute(f"CREATE DATABASE {TEST_DB_NAME}")


def _apply_schema() -> None:
    """Runs the real sql/01_schema.sql verbatim — same DDL the dev DB uses,
    `CREATE EXTENSION IF NOT EXISTS vector` included."""
    with _pg_connect(TEST_DB_NAME, autocommit=True) as conn:
        conn.execute(SCHEMA_SQL.read_text())


# --- CSV -> table column lists, matching app/db/seed.py exactly (kept as a
# separate copy rather than imported: this module's job is a *sample* load
# for tests, seed.py's is the full dev load — different enough call sites
# that duplicating 4 short column lists beats coupling to seed.py's private
# helpers). ---
_CUSTOMERS_COLS = [
    "customer_id", "customer_name", "customer_age", "gender", "customer_segment",
    "customer_city", "customer_state", "customer_country", "region",
    "customer_postal_code", "customer_acquisition_cost",
]
_PRODUCTS_COLS = [
    "product_id", "product_name", "product_category", "product_subcategory",
    "brand", "supplier", "unit_price", "product_cost", "product_rating",
]
_ORDERS_COLS = [
    "order_id", "customer_id", "order_date", "order_time", "order_status",
    "sales_channel", "customer_type", "region", "payment_method", "payment_status",
    "currency", "shipping_method", "warehouse", "delivery_days", "estimated_delivery_days",
    "delivery_status", "return_status", "return_reason", "marketing_channel",
    "campaign_name", "coupon_code", "loyalty_points_earned", "loyalty_points_redeemed",
    "quantity", "gross_sales", "discount_amount", "tax_amount", "shipping_cost",
    "net_sales", "product_cost", "profit", "profit_margin_percentage",
    "customer_lifetime_value", "is_repeat_customer", "customer_order_count",
]
_ORDER_ITEMS_COLS = [
    "order_id", "product_id", "quantity", "unit_price", "discount_percentage",
    "discount_amount", "gross_sales", "tax_amount", "shipping_cost", "net_sales",
    "product_cost", "profit",
]
_RATINGS_RENAME = {
    "order_id": "order_id",
    "customer_id": "customer_id",
    "customer_rating": "rating",
    "review_sentiment": "review_sentiment",
    "customer_review": "customer_review",
}


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Replace pandas NaN/NaT with None so COPY sends real SQL NULLs
    instead of the literal string 'nan' or a NaN float."""
    return df.astype(object).where(df.notna(), None)


def _copy(conn: psycopg.Connection, table: str, cols: list[str], df: pd.DataFrame) -> int:
    df = _clean(df[cols])
    with conn.cursor() as cur:
        with cur.copy(f"COPY {table} ({', '.join(cols)}) FROM STDIN") as copy:
            for row in df.itertuples(index=False, name=None):
                copy.write_row(row)
    return len(df)


def _load_sample_data() -> None:
    """Loads a small, deterministic, FK-consistent slice of the 5 source
    CSVs into the freshly-schema'd `ecommerce_test` DB — see the module
    docstring for the sampling strategy."""
    orders_df = pd.read_csv(DATA_DIR / "ecommerce_sales_customer_analytics_150k.csv")
    orders_sample = orders_df.sample(n=SAMPLE_ORDERS, random_state=42).copy()
    orders_sample["order_date"] = pd.to_datetime(orders_sample["order_date"]).dt.date

    order_items_df = pd.read_csv(DATA_DIR / "order_items.csv")
    order_items_sample = order_items_df[order_items_df["order_id"].isin(orders_sample["order_id"])]

    customers_df = pd.read_csv(DATA_DIR / "customer_master.csv")
    referenced = customers_df["customer_id"].isin(orders_sample["customer_id"])
    customers_sample = pd.concat(
        [customers_df[referenced], customers_df[~referenced].head(EXTRA_CUSTOMERS)]
    )

    products_df = pd.read_csv(DATA_DIR / "product_catalog.csv")
    referenced = products_df["product_id"].isin(order_items_sample["product_id"])
    products_sample = pd.concat(
        [products_df[referenced], products_df[~referenced].head(EXTRA_PRODUCTS)]
    )

    ratings_sample = orders_sample[orders_sample["customer_rating"].notna()]
    ratings_sample = ratings_sample[list(_RATINGS_RENAME.keys())].rename(columns=_RATINGS_RENAME)

    with _pg_connect(TEST_DB_NAME) as conn:
        with conn.transaction():
            _copy(conn, "customers", _CUSTOMERS_COLS, customers_sample)
            _copy(conn, "products", _PRODUCTS_COLS, products_sample)
            _copy(conn, "orders", _ORDERS_COLS, orders_sample)
            _copy(conn, "order_items", _ORDER_ITEMS_COLS, order_items_sample)
            _copy(conn, "ratings", list(_RATINGS_RENAME.values()), ratings_sample)


@pytest.fixture(scope="session")
def test_db() -> Iterator[None]:
    """Session-scoped: (re)builds `ecommerce_test` once per test run — drop,
    create, apply `sql/01_schema.sql`, load the sample data — then drops it
    again at the end. Depend on this fixture (directly or via `client`/
    `db_session` below) to get a ready, isolated database."""
    _recreate_test_database()
    _apply_schema()
    _load_sample_data()
    yield
    # Not load-bearing (the next run recreates it anyway) but tidy: don't
    # leave a stray database sitting in the dev Postgres container.
    with _pg_connect(_ADMIN_DB, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME} WITH (FORCE)")


@pytest.fixture(scope="session")
def _test_session_factory(test_db: None) -> sessionmaker[Session]:
    """Session-scoped engine + sessionmaker bound to `ecommerce_test` — kept
    private to this module; tests should go through `db_session`/`client`."""
    engine = create_engine(_test_database_url(), pool_pre_ping=True, future=True)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


@pytest.fixture
def db_session(_test_session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """One SQLAlchemy session per test, bound to the test DB — for tests
    that want to seed/inspect rows directly rather than only through the
    API (e.g. asserting a row's state after an endpoint call)."""
    session = _test_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(_test_session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    """`TestClient(app)` with FastAPI's `get_db` dependency overridden to
    the test database — every router still runs its real code path (real
    SQL, real constraints), just against `ecommerce_test` instead of the
    dev DB. See the module docstring for the one endpoint this does NOT
    cover (`POST /ai/reports/customer-segments`)."""

    def _override_get_db() -> Generator[Session, None, None]:
        session = _test_session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
