"""
app/models/product.py — SQLAlchemy model for the `products` table.

Mirrors `sql/01_schema.sql` column-for-column; that file is the schema's
source of truth, this model exists for querying/CRUD only.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("unit_price >= 0", name="products_unit_price_check"),
        CheckConstraint("product_cost >= 0", name="products_product_cost_check"),
        CheckConstraint(
            "product_rating >= 0.0 AND product_rating <= 5.0", name="products_product_rating_check"
        ),
        Index("idx_products_category", "product_category"),
        Index("idx_products_brand", "brand"),
    )

    product_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_category: Mapped[str] = mapped_column(String(128), nullable=False)
    product_subcategory: Mapped[str | None] = mapped_column(String(128))
    brand: Mapped[str | None] = mapped_column(String(128))
    supplier: Mapped[str | None] = mapped_column(String(128))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    product_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    product_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())

    # `products.product_id` is ON DELETE RESTRICT from order_items — let
    # Postgres enforce that (raising the IntegrityError the router maps to a 409)
    # instead of SQLAlchemy trying to null out order_items.product_id first
    # (which would fail anyway, since that column is NOT NULL).
    order_items: Mapped[list["OrderItem"]] = relationship(
        back_populates="product", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"Product(product_id={self.product_id!r}, product_name={self.product_name!r})"
