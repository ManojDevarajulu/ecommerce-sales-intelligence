"""
app/schemas/pagination.py — shared pagination helper used by every
list endpoint (customers, products, orders, and later the analytics routes).
"""
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageParams(BaseModel):
    """Query-param dependency for paginated list endpoints.

    Usage: `def list_x(params: PageParams = Depends()): ...`
    """

    page: int = Field(1, ge=1, description="1-indexed page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page (max 100)")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Envelope every paginated list endpoint returns."""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def create(cls, items: list[T], total: int, params: PageParams) -> "PaginatedResponse[T]":
        pages = (total + params.page_size - 1) // params.page_size if params.page_size else 0
        return cls(items=items, total=total, page=params.page, page_size=params.page_size, pages=pages)
