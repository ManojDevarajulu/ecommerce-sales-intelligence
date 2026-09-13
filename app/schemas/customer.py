"""Pydantic schemas and validation models for customer entities."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import CustomerSegment, Gender, Region


class CustomerBase(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=255)
    customer_age: int | None = Field(None, ge=0, le=120)
    gender: Gender | None = None
    customer_segment: CustomerSegment | None = None
    customer_city: str | None = Field(None, max_length=128)
    customer_state: str | None = Field(None, max_length=128)
    customer_country: str | None = Field(None, max_length=128)
    region: Region
    customer_postal_code: str | None = Field(None, max_length=32)
    customer_acquisition_cost: Decimal = Field(Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)


class CustomerCreate(CustomerBase):
    customer_id: str = Field(..., min_length=1, max_length=32)


class CustomerUpdate(BaseModel):
    """PATCH-style partial update — every field optional, no `customer_id`
    (the primary key is immutable once created)."""

    customer_name: str | None = Field(None, min_length=1, max_length=255)
    customer_age: int | None = Field(None, ge=0, le=120)
    gender: Gender | None = None
    customer_segment: CustomerSegment | None = None
    customer_city: str | None = Field(None, max_length=128)
    customer_state: str | None = Field(None, max_length=128)
    customer_country: str | None = Field(None, max_length=128)
    region: Region | None = None
    customer_postal_code: str | None = Field(None, max_length=32)
    customer_acquisition_cost: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)


class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    customer_id: str
    created_at: datetime
