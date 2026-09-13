"""
app/db/reconcile.py — reconciliation check against the published totals.

Compares aggregates computed from the loaded Postgres tables against the
published ground-truth totals in `data/dataset/dataset_statistics.csv`.
Exits non-zero (and prints a FAIL line) if any metric is off by more than a
cent/0.01pp of rounding tolerance — this is the same check that caught the
net_sales-vs-gross_sales definition mismatch during EDA: summing
gross_sales overstates revenue by about 7%, and only this comparison
against the published figure makes that visible.
"""
import os
import sys
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "dataset"


def get_conn() -> psycopg.Connection:
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST_EXTERNAL", "localhost"),
        port=os.getenv("POSTGRES_PORT_EXTERNAL", "5435"),
        user=os.getenv("POSTGRES_USER", "ecommerce"),
        password=os.getenv("POSTGRES_PASSWORD", "change_me"),
        dbname=os.getenv("POSTGRES_DB", "ecommerce"),
    )


def main() -> None:
    stats = pd.read_csv(DATA_DIR / "dataset_statistics.csv").iloc[0]

    def money(s: str) -> float:
        return float(s.replace("$", "").replace(",", ""))

    expected = {
        "total_transactions": int(stats["Total Transactions"]),
        "total_customers": int(stats["Total Customers"]),
        "total_revenue": money(stats["Total Revenue"]),
        "total_profit": money(stats["Total Profit"]),
        "avg_order_value": money(stats["Average Order Value"]),
        "avg_rating": float(stats["Average Rating"]),
        "return_rate": float(stats["Return Rate"].rstrip("%")),
        "cancellation_rate": float(stats["Cancellation Rate"].rstrip("%")),
    }

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM orders;")
            total_transactions = cur.fetchone()[0]

            cur.execute("SELECT count(DISTINCT customer_id) FROM orders;")
            total_customers = cur.fetchone()[0]

            cur.execute("SELECT sum(net_sales), sum(profit), avg(net_sales) FROM orders;")
            total_revenue, total_profit, avg_order_value = cur.fetchone()

            cur.execute("SELECT avg(rating) FROM ratings;")
            avg_rating = cur.fetchone()[0]

            cur.execute(
                "SELECT round(100.0 * count(*) FILTER (WHERE return_status IS NOT NULL) "
                "/ count(*), 2) FROM orders;"
            )
            return_rate = cur.fetchone()[0]

            cur.execute(
                "SELECT round(100.0 * count(*) FILTER (WHERE order_status = 'Cancelled') "
                "/ count(*), 2) FROM orders;"
            )
            cancellation_rate = cur.fetchone()[0]

    actual = {
        "total_transactions": total_transactions,
        "total_customers": total_customers,
        "total_revenue": round(float(total_revenue), 2),
        "total_profit": round(float(total_profit), 2),
        "avg_order_value": round(float(avg_order_value), 2),
        "avg_rating": round(float(avg_rating), 2),
        "return_rate": float(return_rate),
        "cancellation_rate": float(cancellation_rate),
    }

    ok = True
    print(f"{'metric':<22}{'expected':>18}{'actual':>18}   status")
    for key in expected:
        exp, act = expected[key], actual[key]
        match = abs(exp - act) <= 0.01
        ok &= match
        print(f"{key:<22}{exp:>18}{act:>18}   {'OK' if match else 'FAIL'}")

    if not ok:
        sys.exit(1)
    print("\nAll metrics reconciled exactly against dataset_statistics.csv.")


if __name__ == "__main__":
    main()
