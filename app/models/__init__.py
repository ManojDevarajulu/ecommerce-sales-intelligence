"""
app/models/ — SQLAlchemy models, one module per table.

Every model must be imported here so it registers on the shared `Base`
before any relationship or `Base.metadata` call needs to resolve it.
"""
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.rating import Rating

__all__ = ["Customer", "Order", "OrderItem", "Product", "Rating"]
