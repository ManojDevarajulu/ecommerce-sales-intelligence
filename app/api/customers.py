"""
app/api/customers.py — T067-T070: CRUD router for the `customers` resource.

T071 (DELETE, with the 409-on-FK-restrict case) is deliberately not built
yet — out of scope for this batch.
"""
from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Customer
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.schemas.enums import CustomerSegment, Region
from app.schemas.pagination import PageParams, PaginatedResponse

router = APIRouter(prefix="/customers", tags=["customers"])

SortField = Literal["customer_name", "customer_age", "customer_acquisition_cost", "created_at"]


@router.get("", response_model=PaginatedResponse[CustomerResponse])
def list_customers(
    params: PageParams = Depends(),
    region: Region | None = Query(None, description="Filter by region"),
    customer_segment: CustomerSegment | None = Query(None, description="Filter by segment"),
    sort_by: SortField = Query("created_at"),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    db: Session = Depends(get_db),
) -> PaginatedResponse[CustomerResponse]:
    """T067 — list customers with pagination, region/segment filters, and sort."""
    stmt = select(Customer)
    if region is not None:
        stmt = stmt.where(Customer.region == region.value)
    if customer_segment is not None:
        stmt = stmt.where(Customer.customer_segment == customer_segment.value)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    sort_col = getattr(Customer, sort_by)
    stmt = stmt.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
    stmt = stmt.offset(params.offset).limit(params.limit)

    items = db.scalars(stmt).all()
    return PaginatedResponse.create(items=items, total=total, params=params)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: str, db: Session = Depends(get_db)) -> Customer:
    """T068 — get one customer by id, 404 if it doesn't exist."""
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Customer '{customer_id}' not found")
    return customer


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)) -> Customer:
    """T069 — create a customer. Pydantic (`CustomerCreate`) already rejects
    malformed input with a 422 before this body ever runs; a duplicate
    `customer_id` is the one thing only the DB's own PK constraint can
    catch, so that's mapped to a 409 here."""
    customer = Customer(**payload.model_dump())
    db.add(customer)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if isinstance(exc.orig, psycopg.errors.UniqueViolation):
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"Customer '{payload.customer_id}' already exists"
            ) from exc
        raise  # anything else is unexpected here — let it surface as a 500
    db.refresh(customer)
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: str, payload: CustomerUpdate, db: Session = Depends(get_db)) -> Customer:
    """T070 — partial update, reachable via both PUT and PATCH.

    `CustomerUpdate` makes every field optional and this always applies
    `exclude_unset=True`, so PUT here behaves the same as PATCH (only the
    fields actually sent are changed) rather than requiring/replacing the
    full representation — a deliberate simplification since the task list
    treats "PUT/PATCH" as one unit rather than two distinct behaviors.
    """
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Customer '{customer_id}' not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)

    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: str, db: Session = Depends(get_db)) -> None:
    """T071 — delete a customer. `orders.customer_id` is ON DELETE RESTRICT,
    so Postgres itself blocks deleting a customer with order history; that
    FK violation is what maps to the 409 here (not application logic)."""
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Customer '{customer_id}' not found")

    db.delete(customer)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if isinstance(exc.orig, psycopg.errors.ForeignKeyViolation):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Customer '{customer_id}' cannot be deleted: still referenced by existing orders",
            ) from exc
        raise
