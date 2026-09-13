"""
app/services/analytics.py — T084: reusable parametrized query executor for
the analytics endpoints (T085-T090).

The queries themselves stay in `sql/02_analytics_queries.sql` as the
reviewed, documented source of truth; this module is just the plumbing that
lets each analytics endpoint execute a query (or a filtered variant of one)
safely and get back plain, JSON-ready rows — no ORM/CRUD logic belongs here,
only reusable execution machinery.
"""
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def run_query(db: Session, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Execute a parametrized raw SQL SELECT and return rows as plain dicts.

    Always pass caller-supplied values via `params` (`:name` placeholders in
    `sql`) — never string-format a value into `sql` directly. `optional_where`
    below is the safe way to turn optional filters into SQL.
    """
    result = db.execute(text(sql), params or {})
    columns = result.keys()
    return [dict(zip(columns, row)) for row in result.fetchall()]


def optional_where(*conditions: tuple[str, str, Any | None]) -> tuple[str, dict[str, Any]]:
    """Build a `WHERE ...` clause (or `""`) from a set of optional filters.

    Each condition is `(sql_fragment_with_bind_placeholder, param_name,
    value)`; a condition is only included when its value is not None. This
    is how each analytics endpoint turns its optional date/region/category
    query params into safe, parametrized SQL without string-building actual
    values into the query.

    >>> optional_where(
    ...     ("order_date >= :date_from", "date_from", None),
    ...     ("region = :region", "region", "South"),
    ... )
    ('WHERE region = :region', {'region': 'South'})
    """
    clauses: list[str] = []
    params: dict[str, Any] = {}
    for fragment, name, value in conditions:
        if value is not None:
            clauses.append(fragment)
            params[name] = value
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params
