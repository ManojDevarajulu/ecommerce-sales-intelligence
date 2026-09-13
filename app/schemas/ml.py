"""
app/schemas/ml.py — request/response schemas for `POST /ml/predict`.

`PredictRequest` deliberately mirrors a real, not-yet-placed order's raw
fields - `shipping_ratio` and customer-history features are NOT accepted
directly; `ml/predict.py` derives/looks those up itself, the same way a
real checkout-risk-scoring integration would only have the raw
order/customer facts on hand, not the model's internal feature encoding.
Post-order fulfillment fields and post-order accounting values (e.g. discounts)
are excluded to maintain strict pre-fulfillment inference integrity.
Categorical fields reuse the existing `app/schemas/enums.py` vocabularies
(`StrEnum`s) rather than plain `str`, for the same reason every other
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
                          "(same 'primary category' definition used in training)."
    )


class PredictResponse(BaseModel):
    return_probability: float = Field(
        ..., ge=0, le=1,
        description="Model's calibrated probability of order return risk based on pre-fulfillment signals.",
    )
    predicted_label: str = Field(
        ..., description="'Returned' if return_probability >= 0.5, else 'Not Returned'.",
    )
    contributing_factors: list[str] = Field(
        ..., description="Rule-based explanation grounded in training-data reference stats - "
                          "not derived from model internals (no SHAP/coefficients); see ml/predict.py."
    )
