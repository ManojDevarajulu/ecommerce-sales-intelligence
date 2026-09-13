"""Embedding generation client for the RAG knowledge base."""
import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingSettings(BaseSettings):
    """Configuration settings for Ollama embedding integration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "qwen3-embedding:0.6b"
    embedding_dim: int = 1024


settings = EmbeddingSettings()

# Qwen3-Embedding is trained to take a one-line task instruction on the
# QUERY side only (documents are embedded bare). This is the instruction
# Qwen's own retrieval examples use; using it measurably improves
# query->passage matching versus embedding the raw question.
_QUERY_INSTRUCTION = "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: "


class EmbeddingError(RuntimeError):
    """The embedding server is unreachable, returned an error, or returned
    vectors of the wrong shape. Never swallowed - see module docstring."""


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of document chunks. One HTTP call for the whole batch
    (Ollama's /api/embed accepts a list), which is what makes ingest a
    handful of requests rather than one per chunk."""
    if not texts:
        return []
    try:
        response = httpx.post(
            f"{settings.ollama_base_url.rstrip('/')}/api/embed",
            json={"model": settings.embedding_model, "input": texts},
            # First call after the server has been idle also loads the model
            # (~3s observed); the timeout is generous for that, not for a
            # normal call.
            timeout=120.0,
        )
        response.raise_for_status()
        vectors = response.json()["embeddings"]
    except httpx.HTTPError as exc:
        raise EmbeddingError(
            f"embedding request to {settings.ollama_base_url} failed: {exc}"
        ) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise EmbeddingError(f"unexpected response shape from Ollama /api/embed: {exc}") from exc

    # Fail loudly on shape problems here, not later as a pgvector insert
    # error with a less useful message.
    if len(vectors) != len(texts):
        raise EmbeddingError(f"asked for {len(texts)} embeddings, got {len(vectors)}")
    for vector in vectors:
        if len(vector) != settings.embedding_dim:
            raise EmbeddingError(
                f"model {settings.embedding_model!r} returned {len(vector)}-dim vectors, "
                f"but EMBEDDING_DIM={settings.embedding_dim} (and rag_chunks.embedding is "
                f"vector({settings.embedding_dim}))"
            )
    return vectors


def embed_query(question: str) -> list[float]:
    """Embed a user question for similarity search against stored chunks.
    Applies the Qwen3 query instruction prefix - documents never get it."""
    return embed_texts([_QUERY_INSTRUCTION + question])[0]
