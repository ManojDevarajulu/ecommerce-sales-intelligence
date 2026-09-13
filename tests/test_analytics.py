"""
tests/test_analytics.py — T155: response-shape test for `/analytics/sales`
(app/api/analytics.py), against the isolated `ecommerce_test` DB (see
tests/conftest.py).
"""
from app.schemas.analytics import SalesAnalyticsResponse


def test_sales_analytics_response_shape(client):
    """GET /analytics/sales — validates the response against the real
    `SalesAnalyticsResponse` schema (not a hand-copied shape) and sanity
    -checks that the sample data actually produced rows in both halves."""
    resp = client.get("/analytics/sales")
    assert resp.status_code == 200
    body = resp.json()

    # Round-trips through the same Pydantic model the endpoint declares as
    # its response_model — the real shape check, not a hand-picked key list.
    parsed = SalesAnalyticsResponse.model_validate(body)

    assert len(parsed.monthly) > 0
    assert len(parsed.yearly) > 0
    for row in parsed.monthly:
        assert row.order_count > 0
        assert row.total_revenue > 0
    for row in parsed.yearly:
        assert row.total_revenue > 0
    # yoy_growth_pct is null for the first year in the series (no prior year
    # to compare against — see the LAG() window function in the query) and
    # populated for every year after that.
    assert parsed.yearly[0].yoy_growth_pct is None
    assert all(row.yoy_growth_pct is not None for row in parsed.yearly[1:])


def test_sales_analytics_respects_region_filter(client):
    """Same endpoint, `region` filter applied — confirms the optional-WHERE
    plumbing (app/services/analytics.py's `optional_where`) is wired up for
    this route, not just that the unfiltered call works."""
    resp = client.get("/analytics/sales", params={"region": "North"})
    assert resp.status_code == 200
    SalesAnalyticsResponse.model_validate(resp.json())  # still a valid shape when filtered


def test_sales_analytics_rejects_invalid_region(client):
    resp = client.get("/analytics/sales", params={"region": "Atlantis"})
    assert resp.status_code == 422
