"""
tests/test_customers.py — T152-T154: CRUD tests for `/customers`
(app/api/customers.py), against the isolated `ecommerce_test` DB (see
tests/conftest.py).
"""
from decimal import Decimal

from sqlalchemy import text

NEW_CUSTOMER_ID = "CUST-TEST-00001"
MISSING_CUSTOMER_ID = "CUST-DOES-NOT-EXIST"


def _new_customer_payload(customer_id: str = NEW_CUSTOMER_ID) -> dict:
    return {
        "customer_id": customer_id,
        "customer_name": "Ada Lovelace",
        "customer_age": 36,
        "gender": "Female",
        "customer_segment": "Premium",
        "customer_city": "London",
        "customer_state": "England",
        "customer_country": "UK",
        "region": "East",
        "customer_postal_code": "SW1A 1AA",
        "customer_acquisition_cost": "24.50",
    }


# ---------------------------------------------------------------- T152 ----
def test_create_customer_returns_201_with_persisted_data(client):
    """POST /customers — the response echoes back the same fields that were
    sent, plus server-assigned ones (created_at), and a follow-up GET on the
    same id returns the identical data — i.e. it was actually persisted to
    the DB, not just echoed."""
    payload = _new_customer_payload()

    create_resp = client.post("/customers", json=payload)
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()

    assert created["customer_id"] == payload["customer_id"]
    assert created["customer_name"] == payload["customer_name"]
    assert created["customer_age"] == payload["customer_age"]
    assert created["gender"] == payload["gender"]
    assert created["customer_segment"] == payload["customer_segment"]
    assert created["region"] == payload["region"]
    assert Decimal(created["customer_acquisition_cost"]) == Decimal(payload["customer_acquisition_cost"])
    assert created["created_at"]  # server-assigned, just needs to be present

    fetch_resp = client.get(f"/customers/{payload['customer_id']}")
    assert fetch_resp.status_code == 200
    assert fetch_resp.json() == created


def test_create_customer_rejects_invalid_input_with_422(client):
    """Sanity check on the "validate" half of T152: a payload missing the
    required `region` field (no DB default — NOT NULL, no CHECK fallback)
    never reaches Postgres at all."""
    payload = _new_customer_payload("CUST-TEST-INVALID")
    del payload["region"]

    resp = client.post("/customers", json=payload)
    assert resp.status_code == 422


def test_create_duplicate_customer_id_returns_409(client):
    """The PK collision case `create_customer` explicitly maps to 409
    (app/api/customers.py). Self-contained (creates its own row first)
    rather than depending on another test's side effect."""
    payload = _new_customer_payload("CUST-TEST-DUPLICATE")
    first = client.post("/customers", json=payload)
    assert first.status_code == 201, first.text

    second = client.post("/customers", json=payload)
    assert second.status_code == 409


# ---------------------------------------------------------------- T153 ----
def test_get_missing_customer_returns_404(client):
    resp = client.get(f"/customers/{MISSING_CUSTOMER_ID}")
    assert resp.status_code == 404
    assert MISSING_CUSTOMER_ID in resp.json()["detail"]


def test_update_missing_customer_returns_404(client):
    resp = client.patch(f"/customers/{MISSING_CUSTOMER_ID}", json={"customer_name": "Nobody"})
    assert resp.status_code == 404


def test_delete_missing_customer_returns_404(client):
    resp = client.delete(f"/customers/{MISSING_CUSTOMER_ID}")
    assert resp.status_code == 404


# ---------------------------------------------------------------- T154 ----
def test_delete_customer_with_orders_returns_409(client, db_session):
    """A customer referenced by `orders.customer_id` (ON DELETE RESTRICT,
    sql/01_schema.sql) cannot be deleted — Postgres raises a
    ForeignKeyViolation, which `delete_customer` maps to 409 rather than
    letting it surface as a 500."""
    customer_id_with_orders = db_session.execute(text("SELECT customer_id FROM orders LIMIT 1")).scalar()
    assert customer_id_with_orders is not None  # the test DB's sample always has orders

    resp = client.delete(f"/customers/{customer_id_with_orders}")
    assert resp.status_code == 409

    # and it genuinely wasn't deleted
    still_there = client.get(f"/customers/{customer_id_with_orders}")
    assert still_there.status_code == 200
