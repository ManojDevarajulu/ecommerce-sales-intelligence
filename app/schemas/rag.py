"""
app/schemas/rag.py — request/response schemas for POST /ai/rag/query.

The response always carries `sources` next to `answer` (same principle as
the reports keeping `stats` next to `narrative`): every citation is a real
`rag_chunks` row with its similarity score, so a reader can check the
answer against the section it came from instead of taking it on trust.
"""
from pydantic import BaseModel, Field


class RagQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500,
                          examples=["Which category has the highest return rate?"])
    top_k: int | None = Field(None, ge=1, le=10,
                              description="Chunks to retrieve (default: RAG_TOP_K from .env, 4)")


class RagSource(BaseModel):
    n: int = Field(..., description="Citation number - the answer refers to this source as [n]")
    doc_title: str
    section_title: str
    source_file: str = Field(..., description="File under rag/documents/")
    similarity: float = Field(..., description="Cosine similarity to the question, 0-1")
    excerpt: str = Field(..., description="First ~200 characters of the cited section")


class RagMeta(BaseModel):
    generated_by: str = Field(..., description="'openrouter' | 'extractive_fallback' | 'guard'")
    model: str | None = Field(None, description="OpenRouter model id, or null when no LLM call was made")
    embedding_model: str
    similarity_threshold: float
    top_k: int
    best_similarity: float = Field(..., description="Top hit's similarity before the guard was applied")


class RagQueryResponse(BaseModel):
    question: str
    answered: bool = Field(..., description="False when the guard fired or the model found nothing in context")
    answer: str
    sources: list[RagSource]
    meta: RagMeta
