"""
app/models/customer.py — T058: SQLAlchemy model for the `customers` table.

Mirrors `sql/01_schema.sql` column-for-column; that file is the schema's
source of truth, this model exists for querying/CRUD only.
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.rating import Rating


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("customer_age >= 0 AND customer_age <= 120", name="customers_customer_age_check"),
        Index("idx_customers_region", "region"),
        Index("idx_customers_segment", "customer_segment"),
    )

    customer_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_age: Mapped[int | None] = mapped_column()
    gender: Mapped[str | None] = mapped_column(String(32))
    customer_segment: Mapped[str | None] = mapped_column(String(64))
    customer_city: Mapped[str | None] = mapped_column(String(128))
    customer_state: Mapped[str | None] = mapped_column(String(128))
    customer_country: Mapped[str | None] = mapped_column(String(128))
    region: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_postal_code: Mapped[str | None] = mapped_column(String(32))
    customer_acquisition_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())

    # orders.customer_id is ON DELETE RESTRICT and ratings.customer_id is ON
    # DELETE CASCADE at the DB level — passive_deletes=True on both lets
    # Postgres enforce whichever applies directly, instead of SQLAlchemy
    # trying to null out children's (NOT NULL) customer_id columns first.
    orders: Mapped[list["Order"]] = relationship(back_populates="customer", passive_deletes=True)
    ratings: Mapped[list["Rating"]] = relationship(back_populates="customer", passive_deletes=True)

    def __repr__(self) -> str:
        return f"Customer(customer_id={self.customer_id!r}, customer_name={self.customer_name!r})"
