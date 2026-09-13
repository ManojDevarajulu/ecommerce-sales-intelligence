"""
app/services/rag.py — T141/T142: grounded answer generation + citations.

    answer_question("Which category has the highest return rate?", db)
    -> RagQueryResponse(answered=True, answer="Automotive ... [1]", sources=[...])

Three outcomes, in order of precedence:

1. **guard** — retrieval (rag/retrieve.py) found nothing above the
   similarity threshold. No LLM call at all: `answered=False`, a fixed
   "insufficient data" message, empty sources. This is the hallucination
   guard the PDF asks for, and it costs zero OpenRouter requests.
2. **openrouter** — chunks were retrieved and the model answered from
   them. The prompt makes it cite `[n]` and tells it to open with
   INSUFFICIENT DATA if the context doesn't actually contain the answer -
   that's the second half of the guard, for near-topic questions the
   threshold can't catch (see rag/retrieve.py docstring); those come back
   `answered=False` but WITH sources, so the caller can see what was
   considered.
3. **extractive_fallback** — chunks were retrieved but OpenRouter failed
   (no key, network, rate-limited, bad reply). The retrieved sections are
   already human-readable answers, so return the best one verbatim rather
   than an error - same philosophy as the reports' deterministic fallback
   (T117): an LLM outage degrades the answer, it doesn't break the
   endpoint. Also what keeps this endpoint testable without a key.

Citation shape: the LLM only ever sees chunks as "[1] Doc > Section\n..."
and is told to cite by number; `sources` lists those same numbers with
the real doc/section/similarity, so a "[2]" in the answer is checkable.
"""
from sqlalchemy.orm import Session

from app.schemas.rag import RagMeta, RagQueryResponse, RagSource
from app.services.openrouter import chat_completion, settings as openrouter_settings
from rag.embeddings import settings as embedding_settings
from rag.retrieve import RetrievedChunk, retrieve, settings as retrieval_settings

INSUFFICIENT_DATA_MARKER = "INSUFFICIENT DATA"

GUARD_MESSAGE = (
    "Insufficient data: the knowledge base has no section relevant enough to answer this question. "
    "It covers this company's 2021-2025 sales, products, customers, regions, ratings and marketing."
)

EXCERPT_CHARS = 200


def build_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    context = "\n\n".join(
        f"[{n}] {chunk.doc_title} > {chunk.section_title}\n{chunk.chunk_text}"
        for n, chunk in enumerate(chunks, start=1)
    )
    return f"""You are a business analyst assistant for an e-commerce company. Answer the question using ONLY the \
numbered context sections below.

Rules:
- Use only facts and numbers that appear in the context. Do not add outside knowledge, estimates, or numbers \
that are not in the context.
- Cite the section(s) you used by number in square brackets, e.g. [1] or [2][3], right after the sentence \
that relies on them. Every factual sentence needs a citation.
- If the context does not contain the information needed to answer, reply with exactly the words \
"{INSUFFICIENT_DATA_MARKER}" as the first line, followed by one sentence saying what the context does cover \
instead. Do not guess.
- Be concise: a direct answer first, then at most a few supporting sentences. Plain text, no markdown headings.

Context:
{context}

Question: {question}"""


def _sources(chunks: list[RetrievedChunk]) -> list[RagSource]:
    return [
        RagSource(
            n=n,
            doc_title=chunk.doc_title,
            section_title=chunk.section_title,
            source_file=chunk.source_file,
            similarity=chunk.similarity,
            excerpt=chunk.chunk_text[:EXCERPT_CHARS].rstrip() + ("…" if len(chunk.chunk_text) > EXCERPT_CHARS else ""),
        )
        for n, chunk in enumerate(chunks, start=1)
    ]


def _meta(generated_by: str, model: str | None, top_k: int, best_similarity: float) -> RagMeta:
    return RagMeta(
        generated_by=generated_by,
        model=model,
        embedding_model=embedding_settings.embedding_model,
        similarity_threshold=retrieval_settings.rag_similarity_threshold,
        top_k=top_k,
        best_similarity=best_similarity,
    )


def answer_question(question: str, db: Session, top_k: int | None = None) -> RagQueryResponse:
    top_k = top_k or retrieval_settings.rag_top_k
    result = retrieve(question, top_k=top_k, db=db)

    if result.guard_triggered:
        return RagQueryResponse(
            question=question,
            answered=False,
            answer=GUARD_MESSAGE,
            sources=[],
            meta=_meta("guard", None, top_k, result.best_similarity),
        )

    sources = _sources(result.chunks)
    raw = chat_completion(build_prompt(question, result.chunks), temperature=0.1)

    if raw is None:
        best = result.chunks[0]
        return RagQueryResponse(
            question=question,
            answered=True,
            answer=(
                "The language model was unavailable, so here is the most relevant knowledge-base section "
                f"verbatim [1] ({best.doc_title} > {best.section_title}):\n\n{best.chunk_text}"
            ),
            sources=sources,
            meta=_meta("extractive_fallback", None, top_k, result.best_similarity),
        )

    answer = raw.strip()
    answered = not answer.upper().startswith(INSUFFICIENT_DATA_MARKER)
    return RagQueryResponse(
        question=question,
        answered=answered,
        answer=answer,
        sources=sources,
        meta=_meta("openrouter", openrouter_settings.openrouter_model, top_k, result.best_similarity),
    )
