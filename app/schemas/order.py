"""
app/schemas/order.py — T065: Pydantic schemas for the `orders` resource.

Field set mirrors `app/models/order.py` / `sql/01_schema.sql` exactly (the
same explicit 35-column set as `app/db/seed.py`'s `ORDERS_COLS` — the source
CSV also carries customer-demographic and review columns that belong to
`customers`/`ratings`, not `orders`). Constraints mirror the DB's CHECK
constraints (`quantity > 0`); money fields otherwise stay unconstrained on
sign where the data itself isn't always non-negative — `profit` is
genuinely negative for ~0.94% of orders (heavily discounted line items), so
it is deliberately NOT given `ge=0`.
"""
from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import (
    Currency,
    CustomerType,
    DeliveryStatus,
    MarketingChannel,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    Region,
    SalesChannel,
    ShippingMethod,
)


class OrderBase(BaseModel):
    order_date: date
    order_time: time | None = None
    order_status: OrderStatus
    sales_channel: SalesChannel | None = None
    customer_type: CustomerType | None = None
    region: Region | None = None
    payment_method: PaymentMethod | None = None
    payment_status: PaymentStatus | None = None
    currency: Currency = Currency.USD
    shipping_method: ShippingMethod | None = None
    warehouse: str | None = Field(None, max_length=64, pattern=r"^WH-\d{3}$")
    delivery_days: Decimal | None = Field(None, ge=0, max_digits=6, decimal_places=2)
    estimated_delivery_days: Decimal | None = Field(None, ge=0, max_digits=6, decimal_places=2)
    delivery_status: DeliveryStatus
    # This dataset only ever sets return_status to 'Returned' or leaves it
    # NULL (see SCOPE.md) — not a general free-text status field.
    return_status: Literal["Returned"] | None = None
    return_reason: str | None = Field(None, max_length=255)
    marketing_channel: MarketingChannel | None = None
    campaign_name: str | None = Field(None, max_length=128)
    coupon_code: str | None = Field(None, max_length=64)
    loyalty_points_earned: int = Field(0, ge=0)
    loyalty_points_redeemed: int = Field(0, ge=0)
    quantity: int = Field(..., gt=0)
    gross_sales: Decimal = Field(..., max_digits=12, decimal_places=2)
    discount_amount: Decimal = Field(Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    tax_amount: Decimal = Field(Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    shipping_cost: Decimal = Field(Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    net_sales: Decimal = Field(..., max_digits=12, decimal_places=2)
    product_cost: Decimal = Field(..., max_digits=12, decimal_places=2)
    profit: Decimal = Field(..., max_digits=12, decimal_places=2)
    profit_margin_percentage: Decimal | None = Field(None, max_digits=6, decimal_places=2)
    customer_lifetime_value: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    is_repeat_customer: bool = False
    customer_order_count: int = Field(1, ge=1)


class OrderCreate(OrderBase):
    order_id: str = Field(..., min_length=1, max_length=32)
    customer_id: str = Field(..., min_length=1, max_length=32)


class OrderUpdate(BaseModel):
    """PATCH-style partial update — every field optional, no `order_id`/
    `customer_id` (an order can't be reassigned to a different customer)."""

    order_date: date | None = None
    order_time: time | None = None
    order_status: OrderStatus | None = None
    sales_channel: SalesChannel | None = None
    customer_type: CustomerType | None = None
    region: Region | None = None
    payment_method: PaymentMethod | None = None
    payment_status: PaymentStatus | None = None
    currency: Currency | None = None
    shipping_method: ShippingMethod | None = None
    warehouse: str | None = Field(None, max_length=64, pattern=r"^WH-\d{3}$")
    delivery_days: Decimal | None = Field(None, ge=0, max_digits=6, decimal_places=2)
    estimated_delivery_days: Decimal | None = Field(None, ge=0, max_digits=6, decimal_places=2)
    delivery_status: DeliveryStatus | None = None
    return_status: Literal["Returned"] | None = None
    return_reason: str | None = Field(None, max_length=255)
    marketing_channel: MarketingChannel | None = None
    campaign_name: str | None = Field(None, max_length=128)
    coupon_code: str | None = Field(None, max_length=64)
    loyalty_points_earned: int | None = Field(None, ge=0)
    loyalty_points_redeemed: int | None = Field(None, ge=0)
    quantity: int | None = Field(None, gt=0)
    gross_sales: Decimal | None = Field(None, max_digits=12, decimal_places=2)
    discount_amount: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    tax_amount: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    shipping_cost: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    net_sales: Decimal | None = Field(None, max_digits=12, decimal_places=2)
    product_cost: Decimal | None = Field(None, max_digits=12, decimal_places=2)
    profit: Decimal | None = Field(None, max_digits=12, decimal_places=2)
    profit_margin_percentage: Decimal | None = Field(None, max_digits=6, decimal_places=2)
    customer_lifetime_value: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    is_repeat_customer: bool | None = None
    customer_order_count: int | None = Field(None, ge=1)


class OrderResponse(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    customer_id: str
    created_at: datetime
