"""
app/schemas/ml.py — T112: request/response schemas for `POST /ml/predict`.

`PredictRequest` deliberately mirrors a real, not-yet-placed order's raw
fields (see INTERVIEW_PREP.md, 2026-09-13, "T110-114 input contract
decision") - `shipping_ratio`/customer-history features are NOT accepted
directly; `ml/predict.py` derives/looks those up itself, the same way a
real checkout-risk-scoring integration would only have the raw
order/customer facts on hand, not the model's internal feature encoding.
There is deliberately no discount field: `discount_ratio` turned out to be
a target leak and was removed from the model (see ml/train.py, T096).
Categorical fields reuse the existing `app/schemas/enums.py` vocabularies
(T063's `StrEnum`s) rather than plain `str`, for the same reason every other
schema in this project does: invalid values get rejected by Pydantic before
they ever reach the model, and Swagger documents the valid set for free.
"""
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.enums import PaymentMethod, ProductCategory, Region, SalesChannel, ShippingMethod


class PredictRequest(BaseModel):
    customer_id: str = Field(
        ..., description="Existing or brand-new customer id (e.g. 'CUST-000001'); "
                          "an unrecognized id is treated as a first-time customer, not an error."
    )
    gross_sales: Decimal = Field(..., gt=0, description="Order total (gross)")
    shipping_cost: Decimal = Field(..., ge=0, description="Shipping cost for this order")
    sales_channel: SalesChannel
    payment_method: PaymentMethod
    shipping_method: ShippingMethod
    region: Region
    primary_category: ProductCategory = Field(
        ..., description="Category of the order's highest-value line item "
                          "(same 'primary category' definition used in training, T099)."
    )


class PredictResponse(BaseModel):
    return_probability: float = Field(
        ..., ge=0, le=1,
        description="Model's predicted probability of a return. NOTE: the model is only marginally "
                    "better than the ~7% base rate (see ml/MODEL_CARD.md) - most useful for ranking "
                    "orders relative to each other, not as an absolute risk score.",
    )
    predicted_label: str = Field(
        ..., description="'Returned' if return_probability >= 0.5, else 'Not Returned'. With "
                          "class_weight='balanced' this labels roughly half of orders 'Returned'; "
                          "treat as a weak signal.",
    )
    contributing_factors: list[str] = Field(
        ..., description="Rule-based explanation grounded in training-data reference stats - "
                          "not derived from model internals (no SHAP/coefficients); see ml/predict.py."
    )
