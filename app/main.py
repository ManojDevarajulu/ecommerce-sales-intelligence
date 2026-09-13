"""
app/main.py — FastAPI application entrypoint.

Registers the CRUD, analytics, ML, AI-report and RAG routers, exposes a
`/health` probe, and serves the RAG assistant page at `/`.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.ai import rag_router, router as ai_router
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
app.include_router(ai_router)
app.include_router(rag_router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness probe, and the fastest possible Swagger sanity check."""
    return {"status": "ok"}


_ASSISTANT_PAGE = Path(__file__).parent / "static" / "index.html"


@app.get("/", include_in_schema=False)
def assistant_page() -> FileResponse:
    """The RAG chat widget — one static HTML file, no build step.

    Served from the API's own origin so its `fetch("/ai/rag/query")` needs
    no CORS configuration. Hidden from the OpenAPI schema because it's a
    page, not an endpoint.
    """
    return FileResponse(_ASSISTANT_PAGE, media_type="text/html")
