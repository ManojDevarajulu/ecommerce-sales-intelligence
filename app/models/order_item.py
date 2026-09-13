"""
app/models/order_item.py — SQLAlchemy model for the `order_items` table.

Mirrors `sql/01_schema.sql` column-for-column; that file is the schema's
source of truth, this model exists for querying/CRUD only.
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.product import Product


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="order_items_quantity_check"),
        CheckConstraint("unit_price >= 0", name="order_items_unit_price_check"),
        Index("idx_order_items_order_id", "order_id"),
        Index("idx_order_items_product_id", "product_id"),
        Index("idx_order_items_composite", "order_id", "product_id"),
    )

    order_item_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False
    )
    # RESTRICT, not CASCADE: a product with order history can't be deleted
    # out from under it — the delete is refused with a 409.
    product_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("products.product_id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_percentage: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), default=Decimal("0.0000"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    gross_sales: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    shipping_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    net_sales: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    product_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())

    order: Mapped["Order"] = relationship(back_populates="order_items")
    product: Mapped["Product"] = relationship(back_populates="order_items", passive_deletes=True)

    def __repr__(self) -> str:
        return (
            f"OrderItem(order_item_id={self.order_item_id!r}, order_id={self.order_id!r}, "
            f"product_id={self.product_id!r})"
        )
