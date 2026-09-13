"""
app/api/products.py — T072-T076: CRUD router for the `products` resource.
"""
from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Product
from app.schemas.enums import ProductCategory
from app.schemas.pagination import PageParams, PaginatedResponse
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])

SortField = Literal["product_name", "unit_price", "product_cost", "product_rating", "created_at"]


@router.get("", response_model=PaginatedResponse[ProductResponse])
def list_products(
    params: PageParams = Depends(),
    product_category: ProductCategory | None = Query(None, description="Filter by category"),
    brand: str | None = Query(None, description="Filter by brand (exact match)"),
    sort_by: SortField = Query("created_at"),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ProductResponse]:
    """T072 — list products with pagination, category/brand filters, and sort."""
    stmt = select(Product)
    if product_category is not None:
        stmt = stmt.where(Product.product_category == product_category.value)
    if brand is not None:
        stmt = stmt.where(Product.brand == brand)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    sort_col = getattr(Product, sort_by)
    stmt = stmt.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
    stmt = stmt.offset(params.offset).limit(params.limit)

    items = db.scalars(stmt).all()
    return PaginatedResponse.create(items=items, total=total, params=params)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db)) -> Product:
    """T073 — get one product by id, 404 if it doesn't exist."""
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Product '{product_id}' not found")
    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> Product:
    """T074 — create a product; duplicate `product_id` -> 409."""
    product = Product(**payload.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if isinstance(exc.orig, psycopg.errors.UniqueViolation):
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"Product '{payload.product_id}' already exists"
            ) from exc
        raise
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductResponse)
@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(product_id: str, payload: ProductUpdate, db: Session = Depends(get_db)) -> Product:
    """T075 — partial update, reachable via both PUT and PATCH (see the same
    decision logged for T070 in INTERVIEW_PREP.md)."""
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Product '{product_id}' not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: str, db: Session = Depends(get_db)) -> None:
    """T076 — delete a product. `order_items.product_id` is ON DELETE
    RESTRICT, so a product with order history can't be deleted -> 409."""
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Product '{product_id}' not found")

    db.delete(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if isinstance(exc.orig, psycopg.errors.ForeignKeyViolation):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Product '{product_id}' cannot be deleted: still referenced by existing order items",
            ) from exc
        raise
