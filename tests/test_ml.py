"""
tests/test_ml.py — tests for `POST /ml/predict` (app/api/ml.py /
ml/predict.py), against the isolated `ecommerce_test` DB (see
tests/conftest.py). The model itself (`ml/model.joblib`) is the real
trained artifact — nothing here mocks the model, only the DB it reads
customer history from.
"""
from app.schemas.ml import PredictResponse

VALID_PAYLOAD = {
    "customer_id": "CUST-000001",  # need not exist in the sample — see the
                                    # unseen-customer test below for that path
    "gross_sales": "250.00",
    "shipping_cost": "12.50",
    "sales_channel": "Website",
    "payment_method": "Credit Card",
    "shipping_method": "Standard",
    "region": "North",
    "primary_category": "Electronics",
}


def test_predict_valid_input_returns_probability_in_range(client):
    resp = client.post("/ml/predict", json=VALID_PAYLOAD)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    parsed = PredictResponse.model_validate(body)  # real response_model shape
    assert 0.0 <= parsed.return_probability <= 1.0
    assert parsed.predicted_label in {"Returned", "Not Returned"}
    expected_label = "Returned" if parsed.return_probability >= 0.5 else "Not Returned"
    assert parsed.predicted_label == expected_label
    assert len(parsed.contributing_factors) >= 1
    assert all(isinstance(factor, str) and factor for factor in parsed.contributing_factors)


def test_predict_unseen_customer_id_falls_back_to_defaults(client):
    """`build_feature_row` treats an unrecognized `customer_id` as a
    first-time customer rather than an error (ml/predict.py) — same
    endpoint, an id that provably isn't in the sampled data."""
    payload = {**VALID_PAYLOAD, "customer_id": "CUST-NEVER-SEEN-00000"}
    resp = client.post("/ml/predict", json=payload)
    assert resp.status_code == 200, resp.text
    PredictResponse.model_validate(resp.json())


def test_predict_rejects_non_positive_gross_sales(client):
    payload = {**VALID_PAYLOAD, "gross_sales": "0"}
    resp = client.post("/ml/predict", json=payload)
    assert resp.status_code == 422  # Pydantic's gt=0, never reaches build_feature_row


def test_predict_rejects_unknown_category_value(client):
    payload = {**VALID_PAYLOAD, "sales_channel": "Carrier Pigeon"}
    resp = client.post("/ml/predict", json=payload)
    assert resp.status_code == 422  # StrEnum rejects it before the model ever sees it
