"""
tests/test_rag.py — T157: tests for `POST /ai/rag/query` (app/api/ai.py /
app/services/rag.py), against the isolated `ecommerce_test` DB (see
tests/conftest.py).

Both the embedding call (rag/embeddings.py, real Ollama over the network)
and the generation call (app/services/openrouter.py, real OpenRouter) are
monkeypatched here — the same approach used to manually verify T143/T145
(see INTERVIEW_PREP.md), now automated. This keeps the suite fast,
deterministic, and runnable with no network access / API key, and lets the
similarity score be pinned exactly rather than hoping a real embedding
model happens to land on either side of the 0.40 threshold. What's real:
the pgvector column, the cosine-distance query, the threshold/guard logic,
and the citation-building code — only the two network calls are faked.
"""
from sqlalchemy import text

import app.services.rag as rag_service
import rag.retrieve as retrieve_module
from app.schemas.rag import RagQueryResponse

EMBEDDING_DIM = 1024  # fixed by sql/01_schema.sql's `vector(1024)` column


def _unit_vector(axis: int) -> list[float]:
    """An orthonormal basis vector — two different axes are exactly
    orthogonal (cosine similarity 0), and a vector matched against itself
    is exactly parallel (cosine similarity 1). Lets the retrieval test pin
    a similarity score precisely instead of relying on a real embedding
    model's number happening to land on one side of the threshold."""
    v = [0.0] * EMBEDDING_DIM
    v[axis] = 1.0
    return v


def _insert_test_chunk(db_session, *, axis: int) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO rag_chunks (doc_title, section_title, chunk_text, embedding, metadata)
            VALUES (:doc_title, :section_title, :chunk_text, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
            """
        ),
        {
            "doc_title": "Product Analysis",
            "section_title": "Return Rate by Category",
            "chunk_text": "Automotive has the highest return rate among all categories at 7.21%.",
            "embedding": f"[{','.join(str(x) for x in _unit_vector(axis))}]",
            "metadata": '{"source_file": "product_analysis.md"}',
        },
    )
    db_session.commit()


def _clear_rag_chunks(db_session) -> None:
    db_session.execute(text("DELETE FROM rag_chunks"))
    db_session.commit()


def test_rag_query_returns_citations(client, db_session, monkeypatch):
    """A question that embeds identically to a stored chunk (similarity
    1.0, comfortably above the 0.40 guard) gets a real citation back:
    `sources[0]` traces to that exact row, and the answer references it."""
    _insert_test_chunk(db_session, axis=0)
    try:
        monkeypatch.setattr(retrieve_module, "embed_query", lambda question: _unit_vector(0))
        monkeypatch.setattr(
            rag_service, "chat_completion",
            lambda prompt, temperature=0.1: "Automotive has the highest return rate at 7.21% [1].",
        )

        resp = client.post("/ai/rag/query", json={"question": "Which category has the highest return rate?"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        parsed = RagQueryResponse.model_validate(body)

        assert parsed.answered is True
        assert parsed.meta.generated_by == "openrouter"
        assert "[1]" in parsed.answer
        assert len(parsed.sources) == 1
        source = parsed.sources[0]
        assert source.n == 1
        assert source.doc_title == "Product Analysis"
        assert source.section_title == "Return Rate by Category"
        assert source.source_file == "product_analysis.md"
        assert source.similarity == 1.0
    finally:
        _clear_rag_chunks(db_session)


def test_rag_query_hallucination_guard(client, db_session, monkeypatch):
    """An off-topic question — embedded here as a vector orthogonal to
    every stored chunk, similarity 0.0 — never clears the 0.40 guard.
    Asserts the zero-LLM-call contract, not just the response shape:
    `chat_completion` raises if it's ever invoked."""
    _insert_test_chunk(db_session, axis=0)
    try:
        monkeypatch.setattr(retrieve_module, "embed_query", lambda question: _unit_vector(1))

        def _must_not_be_called(*args, **kwargs):
            raise AssertionError("chat_completion must not be called when the guard fires")

        monkeypatch.setattr(rag_service, "chat_completion", _must_not_be_called)

        resp = client.post("/ai/rag/query", json={"question": "What is the capital of France?"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        parsed = RagQueryResponse.model_validate(body)

        assert parsed.answered is False
        assert parsed.meta.generated_by == "guard"
        assert parsed.meta.model is None
        assert parsed.meta.best_similarity == 0.0
        assert parsed.sources == []
        assert parsed.answer == rag_service.GUARD_MESSAGE
    finally:
        _clear_rag_chunks(db_session)


def test_rag_query_rejects_too_short_question(client):
    resp = client.post("/ai/rag/query", json={"question": "hi"})  # min_length=3
    assert resp.status_code == 422


def test_rag_query_embedding_service_down_returns_503(client, monkeypatch):
    from rag.embeddings import EmbeddingError

    def _raise(question: str) -> list[float]:
        raise EmbeddingError("embedding request to http://fake-ollama failed: connection refused")

    monkeypatch.setattr(retrieve_module, "embed_query", _raise)

    resp = client.post("/ai/rag/query", json={"question": "Which category has the highest return rate?"})
    assert resp.status_code == 503
