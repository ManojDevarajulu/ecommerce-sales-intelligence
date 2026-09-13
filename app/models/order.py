"""
app/models/order.py — SQLAlchemy model for the `orders` table.

Mirrors `sql/01_schema.sql` column-for-column — the same explicit 35-column
set used by `app/db/seed.py`'s `ORDERS_COLS` (the source CSV also carries
customer-demographic and review columns that belong to `customers`/
`ratings` instead, not `orders`).
"""
from datetime import date as date_, datetime, time as time_
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base

if TYPE_CHECKING:
    # Import cycle: Customer/OrderItem/Rating each relate back to Order, so
    # these are real imports for the type checker only, not at runtime —
    # SQLAlchemy resolves the string names below via its own class registry
    # once every model in app/models/__init__.py has been imported.
    from app.models.customer import Customer
    from app.models.order_item import OrderItem
    from app.models.rating import Rating


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="orders_quantity_check"),
        Index("idx_orders_customer_id", "customer_id"),
        Index("idx_orders_order_date", "order_date"),
        Index("idx_orders_order_status", "order_status"),
        Index("idx_orders_delivery_status", "delivery_status"),
        Index("idx_orders_return_status", "return_status"),
        Index("idx_orders_region", "region"),
        Index("idx_orders_sales_channel", "sales_channel"),
        Index("idx_orders_marketing_channel", "marketing_channel"),
    )

    order_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    # RESTRICT, not CASCADE: deleting a customer with order history must be
    # blocked with a 409, never silently wipe their orders.
    customer_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("customers.customer_id", ondelete="RESTRICT"), nullable=False
    )
    order_date: Mapped[date_] = mapped_column(Date, nullable=False)
    order_time: Mapped[time_ | None] = mapped_column(Time)
    order_status: Mapped[str] = mapped_column(String(64), nullable=False)
    sales_channel: Mapped[str | None] = mapped_column(String(64))
    customer_type: Mapped[str | None] = mapped_column(String(64))
    region: Mapped[str | None] = mapped_column(String(64))
    payment_method: Mapped[str | None] = mapped_column(String(64))
    payment_status: Mapped[str | None] = mapped_column(String(64))
    currency: Mapped[str | None] = mapped_column(String(16), default="USD")
    shipping_method: Mapped[str | None] = mapped_column(String(64))
    warehouse: Mapped[str | None] = mapped_column(String(64))
    delivery_days: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    estimated_delivery_days: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    delivery_status: Mapped[str] = mapped_column(String(64), nullable=False)
    return_status: Mapped[str | None] = mapped_column(String(64))
    return_reason: Mapped[str | None] = mapped_column(String(255))
    marketing_channel: Mapped[str | None] = mapped_column(String(64))
    campaign_name: Mapped[str | None] = mapped_column(String(128))
    coupon_code: Mapped[str | None] = mapped_column(String(64))
    loyalty_points_earned: Mapped[int | None] = mapped_column(default=0)
    loyalty_points_redeemed: Mapped[int | None] = mapped_column(default=0)
    quantity: Mapped[int] = mapped_column(nullable=False)
    gross_sales: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    shipping_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    net_sales: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    product_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    profit_margin_percentage: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    customer_lifetime_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    is_repeat_customer: Mapped[bool | None] = mapped_column(default=False)
    customer_order_count: Mapped[int | None] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())

    customer: Mapped["Customer"] = relationship(back_populates="orders")
    # order_items/rating are both ON DELETE CASCADE at the DB level;
    # passive_deletes=True lets Postgres do that cascade directly instead of
    # SQLAlchemy loading the children and issuing individual DELETEs first.
    order_items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", passive_deletes=True
    )
    rating: Mapped[Optional["Rating"]] = relationship(
        back_populates="order", uselist=False, passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"Order(order_id={self.order_id!r}, customer_id={self.customer_id!r}, net_sales={self.net_sales!r})"
