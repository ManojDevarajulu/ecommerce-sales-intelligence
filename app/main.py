"""
app/main.py — T082: FastAPI application entrypoint. Registers every router.
"""
from fastapi import FastAPI

from app.api.analytics import router as analytics_router
from app.api.customers import router as customers_router
from app.api.ml import router as ml_router
from app.api.orders import router as orders_router
from app.api.products import router as products_router

app = FastAPI(
    title="E-Commerce Sales Intelligence Platform",
    description="Piquota Digital Inc 2-day technical assessment API.",
    version="0.1.0",
)

app.include_router(customers_router)
app.include_router(products_router)
app.include_router(orders_router)
app.include_router(analytics_router)
app.include_router(ml_router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness probe, and the fastest possible Swagger sanity check."""
    return {"status": "ok"}
