"""Request and response schemas for order return risk prediction."""
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.enums import PaymentMethod, ProductCategory, Region, SalesChannel, ShippingMethod


class PredictRequest(BaseModel):
    customer_id: str = Field(
        ..., description="Customer identifier (e.g. 'CUST-000001'). Unrecognized IDs default to first-time customer baseline."
    )
    gross_sales: Decimal = Field(..., gt=0, description="Order total (gross)")
    shipping_cost: Decimal = Field(..., ge=0, description="Shipping cost for this order")
    sales_channel: SalesChannel
    payment_method: PaymentMethod
    shipping_method: ShippingMethod
    region: Region
    primary_category: ProductCategory = Field(..., description="Primary product category for the order")


class PredictResponse(BaseModel):
    return_probability: float = Field(
        ..., ge=0, le=1,
        description="Model's calibrated probability of order return risk based on pre-fulfillment signals.",
    )
    predicted_label: str = Field(
        ..., description="'Returned' if return_probability >= 0.5, else 'Not Returned'.",
    )
    contributing_factors: list[str] = Field(
        ..., description="Key risk factors contributing to the return prediction."
    )
