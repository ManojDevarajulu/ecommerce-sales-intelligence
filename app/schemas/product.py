"""
app/schemas/product.py — T064: Pydantic schemas for the `products` resource.

Field constraints mirror `sql/01_schema.sql`'s CHECK constraints exactly
(`unit_price`/`product_cost` >= 0, `product_rating` 0.0-5.0).
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import ProductCategory


class ProductBase(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=255)
    product_category: ProductCategory
    product_subcategory: str | None = Field(None, max_length=128)
    brand: str | None = Field(None, max_length=128)
    supplier: str | None = Field(None, max_length=128)
    unit_price: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    product_cost: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    product_rating: Decimal | None = Field(None, ge=0, le=5, max_digits=3, decimal_places=2)


class ProductCreate(ProductBase):
    product_id: str = Field(..., min_length=1, max_length=32)


class ProductUpdate(BaseModel):
    """PATCH-style partial update — every field optional, no `product_id`."""

    product_name: str | None = Field(None, min_length=1, max_length=255)
    product_category: ProductCategory | None = None
    product_subcategory: str | None = Field(None, max_length=128)
    brand: str | None = Field(None, max_length=128)
    supplier: str | None = Field(None, max_length=128)
    unit_price: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    product_cost: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    product_rating: Decimal | None = Field(None, ge=0, le=5, max_digits=3, decimal_places=2)


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    product_id: str
    created_at: datetime
