"""
app/schemas/analytics.py — typed response models for the 6 analytics
endpoints (T085-T090), add-on alongside them.

Row shapes mirror `sql/02_analytics_queries.sql`'s columns exactly (same
query, just executed through `app/services/analytics.py` with optional
filters) — these models exist purely for self-documenting Swagger output
and response-shape validation, not for request validation (there's no
Create/Update side to an analytics result).
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


# ---------------------------------------------------------------- /sales
class MonthlyRevenue(BaseModel):
    month: date
    order_count: int
    total_revenue: Decimal


class YearlyRevenue(BaseModel):
    year: int
    total_revenue: Decimal
    yoy_growth_pct: Decimal | None = None


class SalesAnalyticsResponse(BaseModel):
    monthly: list[MonthlyRevenue]
    yearly: list[YearlyRevenue]


# ------------------------------------------------------------- /customers
class TopCustomer(BaseModel):
    customer_id: str
    customer_name: str
    customer_segment: str | None = None
    region: str | None = None
    order_count: int
    total_revenue: Decimal
    avg_order_value: Decimal


class CustomerAnalyticsResponse(BaseModel):
    top_customers: list[TopCustomer]


# -------------------------------------------------------------- /products
class TopProduct(BaseModel):
    product_id: str
    product_name: str
    product_category: str
    units_sold: int
    total_revenue: Decimal


class CategoryRevenue(BaseModel):
    product_category: str
    total_revenue: Decimal
    total_profit: Decimal
    margin_pct: Decimal | None = None


class ProductAnalyticsResponse(BaseModel):
    top_products: list[TopProduct]
    by_category: list[CategoryRevenue]


# --------------------------------------------------------------- /regions
class RegionFulfillment(BaseModel):
    region: str
    order_count: int
    total_revenue: Decimal
    on_time_pct: Decimal | None = None
    delayed_pct: Decimal | None = None
    early_pct: Decimal | None = None
    cancelled_pending_or_returned_pct: Decimal | None = None


class RegionAnalyticsResponse(BaseModel):
    regions: list[RegionFulfillment]


# ------------------------------------------------------------- /marketing
class ChannelAOV(BaseModel):
    sales_channel: str
    order_count: int
    avg_order_value: Decimal
    total_revenue: Decimal


class ChannelROI(BaseModel):
    marketing_channel: str
    customers_acquired: int
    lifetime_revenue: Decimal
    total_acquisition_cost: Decimal
    revenue_per_acquisition_dollar: Decimal | None = None


class MarketingAnalyticsResponse(BaseModel):
    channel_aov: list[ChannelAOV]
    channel_roi: list[ChannelROI]


# --------------------------------------------------------------- /ratings
class RatingDistributionRow(BaseModel):
    rating: Decimal
    num_ratings: int


class RatingByDeliveryStatus(BaseModel):
    delivery_status: str
    num_ratings: int
    avg_rating: Decimal


class ReturnRateByCategory(BaseModel):
    product_category: str
    orders_with_category: int
    returned_orders: int
    return_rate_pct: Decimal


class RatingAnalyticsResponse(BaseModel):
    rating_distribution: list[RatingDistributionRow]
    rating_by_delivery_status: list[RatingByDeliveryStatus]
    overall_return_rate_pct: Decimal
    return_rate_by_category: list[ReturnRateByCategory]
