"""Similarity search and threshold-based hallucination guardrail."""
import json
from dataclasses import dataclass

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from rag.embeddings import embed_query


class RetrievalSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Calibrated, not guessed - see rag/calibrate.py and the module docstring.
    rag_similarity_threshold: float = 0.40
    rag_top_k: int = 4


settings = RetrievalSettings()


@dataclass
class RetrievedChunk:
    id: int
    doc_title: str
    section_title: str
    source_file: str
    chunk_text: str
    similarity: float


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk]  # only those at/above the threshold, best first
    best_similarity: float  # of the top hit BEFORE thresholding (0.0 if the table is empty)
    threshold: float

    @property
    def guard_triggered(self) -> bool:
        return not self.chunks


def search(question: str, top_k: int, db: Session | None = None) -> list[RetrievedChunk]:
    """Raw nearest-neighbour search - no threshold. Kept separate from
    `retrieve()` so calibration and debugging can see what the guard
    would have hidden."""
    query_vector = json.dumps(embed_query(question))
    sql = text(
        """
        SELECT id, doc_title, section_title, metadata->>'source_file' AS source_file,
               chunk_text, 1 - (embedding <=> CAST(:q AS vector)) AS similarity
        FROM rag_chunks
        ORDER BY embedding <=> CAST(:q AS vector)
        LIMIT :k
        """
    )
    owns_session = db is None
    db = db or SessionLocal()
    try:
        rows = db.execute(sql, {"q": query_vector, "k": top_k}).mappings().all()
    finally:
        if owns_session:
            db.close()
    return [
        RetrievedChunk(
            id=row["id"],
            doc_title=row["doc_title"],
            section_title=row["section_title"],
            source_file=row["source_file"],
            chunk_text=row["chunk_text"],
            similarity=round(float(row["similarity"]), 4),
        )
        for row in rows
    ]


def retrieve(
    question: str,
    top_k: int | None = None,
    threshold: float | None = None,
    db: Session | None = None,
) -> RetrievalResult:
    """Search, then apply the guard. `top_k`/`threshold` default to the
    .env-configured values; overridable so tests and calibration can pin
    them explicitly."""
    top_k = top_k or settings.rag_top_k
    threshold = settings.rag_similarity_threshold if threshold is None else threshold
    hits = search(question, top_k=top_k, db=db)
    best = hits[0].similarity if hits else 0.0
    return RetrievalResult(
        chunks=[hit for hit in hits if hit.similarity >= threshold],
        best_similarity=best,
        threshold=threshold,
    )
