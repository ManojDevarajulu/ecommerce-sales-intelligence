"""
app/api/orders.py — T077-T081: CRUD router for the `orders` resource.
"""
from datetime import date
from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Order
from app.schemas.enums import OrderStatus
from app.schemas.order import OrderCreate, OrderResponse, OrderUpdate
from app.schemas.pagination import PageParams, PaginatedResponse

router = APIRouter(prefix="/orders", tags=["orders"])

SortField = Literal["order_date", "net_sales", "profit", "created_at"]


@router.get("", response_model=PaginatedResponse[OrderResponse])
def list_orders(
    params: PageParams = Depends(),
    customer_id: str | None = Query(None, description="Filter by customer"),
    order_status: OrderStatus | None = Query(None, description="Filter by order status"),
    date_from: date | None = Query(None, description="order_date >= this date"),
    date_to: date | None = Query(None, description="order_date <= this date"),
    sort_by: SortField = Query("order_date"),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    db: Session = Depends(get_db),
) -> PaginatedResponse[OrderResponse]:
    """T077 — list orders with pagination, date-range/status/customer
    filters, and sort."""
    stmt = select(Order)
    if customer_id is not None:
        stmt = stmt.where(Order.customer_id == customer_id)
    if order_status is not None:
        stmt = stmt.where(Order.order_status == order_status.value)
    if date_from is not None:
        stmt = stmt.where(Order.order_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Order.order_date <= date_to)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    sort_col = getattr(Order, sort_by)
    stmt = stmt.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
    stmt = stmt.offset(params.offset).limit(params.limit)

    items = db.scalars(stmt).all()
    return PaginatedResponse.create(items=items, total=total, params=params)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, db: Session = Depends(get_db)) -> Order:
    """T078 — get one order by id, 404 if it doesn't exist."""
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Order '{order_id}' not found")
    return order


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)) -> Order:
    """T079 — create an order. Unlike customers/products, this can fail two
    different ways at the DB layer, and they mean different things to a
    caller: a duplicate `order_id` is a conflict with an existing resource
    (409); a `customer_id` that doesn't exist is a bad reference in the
    submitted data (422, alongside Pydantic's own validation errors) — not
    a 409, since there's no competing *order* it conflicts with."""
    order = Order(**payload.model_dump())
    db.add(order)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if isinstance(exc.orig, psycopg.errors.UniqueViolation):
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"Order '{payload.order_id}' already exists"
            ) from exc
        if isinstance(exc.orig, psycopg.errors.ForeignKeyViolation):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Customer '{payload.customer_id}' does not exist",
            ) from exc
        raise
    db.refresh(order)
    return order


@router.put("/{order_id}", response_model=OrderResponse)
@router.patch("/{order_id}", response_model=OrderResponse)
def update_order(order_id: str, payload: OrderUpdate, db: Session = Depends(get_db)) -> Order:
    """T080 — partial update, reachable via both PUT and PATCH (same
    decision as T070/T075). `OrderUpdate` doesn't accept `customer_id`, so
    there's no FK-violation case to handle here."""
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Order '{order_id}' not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, field, value)

    db.commit()
    db.refresh(order)
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: str, db: Session = Depends(get_db)) -> None:
    """T081 — delete an order. `order_items.order_id` and `ratings.order_id`
    are both ON DELETE CASCADE, so this cleanly removes the order's line
    items and rating too — no 409 case here, unlike customers/products."""
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Order '{order_id}' not found")

    db.delete(order)
    db.commit()
