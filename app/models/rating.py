"""
app/models/rating.py — SQLAlchemy model for the `ratings` table.

Mirrors `sql/01_schema.sql` column-for-column. Split from `orders` (see
`docs/ER_DIAGRAM.md`) since 24,557 of 138,116 orders were never delivered
and so have no rating — a row only exists here when one was actually given.
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.order import Order


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (
        CheckConstraint("rating >= 1.0 AND rating <= 5.0", name="ratings_rating_check"),
        Index("idx_ratings_order_id", "order_id"),
        Index("idx_ratings_customer_id", "customer_id"),
        Index("idx_ratings_rating", "rating"),
        Index("idx_ratings_sentiment", "review_sentiment"),
    )

    rating_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False, unique=True
    )
    customer_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False
    )
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 1), nullable=False)
    review_sentiment: Mapped[str | None] = mapped_column(String(32))
    customer_review: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())

    order: Mapped["Order"] = relationship(back_populates="rating")
    customer: Mapped["Customer"] = relationship(back_populates="ratings", passive_deletes=True)

    def __repr__(self) -> str:
        return f"Rating(rating_id={self.rating_id!r}, order_id={self.order_id!r}, rating={self.rating!r})"
