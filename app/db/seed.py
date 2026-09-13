"""
app/db/seed.py — Bulk-load the 4 source CSVs into Postgres via COPY.

Run from the project root with the local .venv (not inside Docker), so it
connects to the host-mapped port (localhost:5435), matching the .env note
in `docker-compose.yml`/`.env`.

Load order matters for FK dependencies:
    customers, products  (no FKs)
    -> orders             (FK -> customers)
    -> order_items        (FK -> orders, products)
    -> ratings            (FK -> orders, customers; only non-null ratings)

Each loader selects its columns explicitly rather than copying the CSV
wholesale: the orders CSV also carries denormalized customer demographics
and review fields, which belong in `customers` and `ratings` instead.
"""
import os
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "dataset"


def get_conn() -> psycopg.Connection:
    """Host-side connection — this script runs via the local venv, so it
    uses the host-mapped port (5435), not the Docker-internal one (5432)."""
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST_EXTERNAL", "localhost"),
        port=os.getenv("POSTGRES_PORT_EXTERNAL", "5435"),
        user=os.getenv("POSTGRES_USER", "ecommerce"),
        password=os.getenv("POSTGRES_PASSWORD", "change_me"),
        dbname=os.getenv("POSTGRES_DB", "ecommerce"),
    )


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


def load_customers(conn) -> int:
    """Load the customer dimension from `customer_master.csv`."""
    df = pd.read_csv(DATA_DIR / "customer_master.csv")
    cols = [
        "customer_id", "customer_name", "customer_age", "gender", "customer_segment",
        "customer_city", "customer_state", "customer_country", "region",
        "customer_postal_code", "customer_acquisition_cost",
    ]
    return _copy(conn, "customers", cols, df)


def load_products(conn) -> int:
    """Load the product catalog from `product_catalog.csv`."""
    df = pd.read_csv(DATA_DIR / "product_catalog.csv")
    cols = [
        "product_id", "product_name", "product_category", "product_subcategory",
        "brand", "supplier", "unit_price", "product_cost", "product_rating",
    ]
    return _copy(conn, "products", cols, df)


# Explicit column selection/order for `orders` — the source CSV also carries
# denormalized customer demographic fields (name, age, gender, city, state,
# country, postal code) and review fields (rating, sentiment, review text),
# which belong to `customers` and `ratings` respectively, not `orders`.
ORDERS_COLS = [
    "order_id", "customer_id", "order_date", "order_time", "order_status",
    "sales_channel", "customer_type", "region", "payment_method", "payment_status",
    "currency", "shipping_method", "warehouse", "delivery_days", "estimated_delivery_days",
    "delivery_status", "return_status", "return_reason", "marketing_channel",
    "campaign_name", "coupon_code", "loyalty_points_earned", "loyalty_points_redeemed",
    "quantity", "gross_sales", "discount_amount", "tax_amount", "shipping_cost",
    "net_sales", "product_cost", "profit", "profit_margin_percentage",
    "customer_lifetime_value", "is_repeat_customer", "customer_order_count",
]


def load_orders(conn) -> int:
    """Load order-level facts from the main sales CSV."""
    df = pd.read_csv(DATA_DIR / "ecommerce_sales_customer_analytics_150k.csv")
    df["order_date"] = pd.to_datetime(df["order_date"]).dt.date
    return _copy(conn, "orders", ORDERS_COLS, df)


def load_order_items(conn) -> int:
    """Load line items from `order_items.csv`."""
    df = pd.read_csv(DATA_DIR / "order_items.csv")
    cols = [
        "order_id", "product_id", "quantity", "unit_price", "discount_percentage",
        "discount_amount", "gross_sales", "tax_amount", "shipping_cost", "net_sales",
        "product_cost", "profit",
    ]
    return _copy(conn, "order_items", cols, df)


def load_ratings(conn) -> int:
    """Load ratings, derived from the orders CSV.

    Only rows with a non-null `customer_rating` become rows here - the
    ~17.8% of orders that were never delivered have nothing to rate, which
    is exactly why ratings is its own table rather than nullable columns
    on `orders`.
    """
    df = pd.read_csv(DATA_DIR / "ecommerce_sales_customer_analytics_150k.csv")
    df = df[df["customer_rating"].notna()]
    rename = {
        "order_id": "order_id",
        "customer_id": "customer_id",
        "customer_rating": "rating",
        "review_sentiment": "review_sentiment",
        "customer_review": "customer_review",
    }
    df = df[list(rename.keys())].rename(columns=rename)
    return _copy(conn, "ratings", list(rename.values()), df)


def main() -> None:
    with get_conn() as conn:
        with conn.transaction():
            print(f"customers:   {load_customers(conn):>7,}")
            print(f"products:    {load_products(conn):>7,}")
            print(f"orders:      {load_orders(conn):>7,}")
            print(f"order_items: {load_order_items(conn):>7,}")
            print(f"ratings:     {load_ratings(conn):>7,}")


if __name__ == "__main__":
    main()
