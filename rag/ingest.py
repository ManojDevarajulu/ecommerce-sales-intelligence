"""
rag/ingest.py — knowledge-base ingest.

    python -m rag.ingest            # chunk -> embed -> (re)load rag_chunks
    python -m rag.ingest --dry-run  # chunk only, print what would be stored

Pipeline: rag/documents/*.md -> one chunk per `##` section -> embeddings
(rag/embeddings.py, Ollama) -> rag_chunks (pgvector).

Chunking = one chunk per `##` section, no further splitting. The documents
were written for exactly this: every section restates its own
entity, metric definition and denominator so it makes sense on its own,
because at query time a section is retrieved and shown to the LLM without
its neighbours. The embedding model's 32K-token context is far larger than
any section (longest is ~400 words), so there is no truncation to work
around - which is what would have forced sub-section splitting under the
original 256-token MiniLM plan. The text before a document's first `##`
(the source/definitions preamble) becomes its own "About this document"
chunk rather than being dropped - it's where the net-vs-gross and
order-level-vs-item-level caveats live.

Idempotent: every run wipes rag_chunks and reloads it in full. The whole
knowledge base is this one folder, the load takes seconds, and it keeps
"re-run ingest" the only thing anyone needs to know after editing a doc -
no partial-update bookkeeping to get wrong.
"""
import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text

from app.db.session import engine
from rag.embeddings import EmbeddingError, embed_texts, settings as embedding_settings

DOCUMENTS_DIR = Path(__file__).parent / "documents"
PREAMBLE_SECTION_TITLE = "About this document"


@dataclass
class Chunk:
    source_file: str
    doc_title: str
    section_title: str
    section_index: int
    text: str

    @property
    def embedding_input(self) -> str:
        # The title lines are part of what gets embedded (so "regional" /
        # "rating" context is in the vector even when the body never says
        # the word) but are NOT stored in chunk_text - the citation shows
        # them separately.
        return f"{self.doc_title}\n{self.section_title}\n{self.text}"

    @property
    def word_count(self) -> int:
        return len(self.text.split())


def chunk_markdown(path: Path) -> list[Chunk]:
    """Split one markdown file into chunks at `##` headings."""
    lines = path.read_text(encoding="utf-8").splitlines()

    doc_title = path.stem
    body_start = 0
    if lines and lines[0].startswith("# "):
        doc_title = lines[0][2:].strip()
        body_start = 1

    # Walk the lines once, opening a new section at every `## ` heading.
    sections: list[tuple[str, list[str]]] = [(PREAMBLE_SECTION_TITLE, [])]
    for line in lines[body_start:]:
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        else:
            sections[-1][1].append(line)

    chunks = []
    for index, (title, section_lines) in enumerate(sections):
        section_text = "\n".join(section_lines).strip()
        if not section_text:
            continue  # a heading with nothing under it - nothing to retrieve
        chunks.append(
            Chunk(
                source_file=path.name,
                doc_title=doc_title,
                section_title=title,
                section_index=index,
                text=section_text,
            )
        )
    return chunks


def load_all_chunks(documents_dir: Path = DOCUMENTS_DIR) -> list[Chunk]:
    paths = sorted(documents_dir.glob("*.md"))
    if not paths:
        raise FileNotFoundError(f"no .md files in {documents_dir}")
    chunks = []
    for path in paths:
        chunks.extend(chunk_markdown(path))
    return chunks


def store_chunks(chunks: list[Chunk], vectors: list[list[float]]) -> None:
    """Replace the contents of rag_chunks with these chunks + vectors, in one
    transaction - a failure mid-way leaves the previous load intact."""
    rows = [
        {
            "doc_title": chunk.doc_title,
            "section_title": chunk.section_title,
            "chunk_text": chunk.text,
            # pgvector's text input format is the JSON list format, so
            # json.dumps + CAST(... AS vector) avoids needing the pgvector
            # SQLAlchemy adapter just for inserts.
            "embedding": json.dumps(vector),
            "metadata": json.dumps(
                {
                    "source_file": chunk.source_file,
                    "section_index": chunk.section_index,
                    "word_count": chunk.word_count,
                    "embedding_model": embedding_settings.embedding_model,
                    "embedding_dim": embedding_settings.embedding_dim,
                }
            ),
        }
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM rag_chunks"))
        conn.execute(
            text(
                """
                INSERT INTO rag_chunks (doc_title, section_title, chunk_text, embedding, metadata)
                VALUES (:doc_title, :section_title, :chunk_text,
                        CAST(:embedding AS vector), CAST(:metadata AS jsonb))
                """
            ),
            rows,
        )


def verify_store(expected_rows: int) -> None:
    """Read back what was written - rule 5 (verify, don't assume)."""
    with engine.connect() as conn:
        n_rows = conn.execute(text("SELECT COUNT(*) FROM rag_chunks")).scalar()
        bad_dims = conn.execute(
            text("SELECT COUNT(*) FROM rag_chunks WHERE vector_dims(embedding) <> :dim"),
            {"dim": embedding_settings.embedding_dim},
        ).scalar()
        per_doc = conn.execute(
            text("SELECT doc_title, COUNT(*) FROM rag_chunks GROUP BY doc_title ORDER BY doc_title")
        ).fetchall()
    if n_rows != expected_rows or bad_dims:
        raise RuntimeError(
            f"verification failed: {n_rows} rows stored (expected {expected_rows}), "
            f"{bad_dims} with wrong vector dimension"
        )
    print(f"verified: {n_rows} chunks stored, all {embedding_settings.embedding_dim}-dim")
    for doc_title, count in per_doc:
        print(f"  {count:>3}  {doc_title}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="chunk and print, don't embed or store")
    args = parser.parse_args(argv)

    chunks = load_all_chunks()
    print(f"{len(chunks)} chunks from {len({c.source_file for c in chunks})} documents")
    if args.dry_run:
        for chunk in chunks:
            print(f"  [{chunk.word_count:>4} words] {chunk.source_file} > {chunk.section_title}")
        return 0

    print(f"embedding with {embedding_settings.embedding_model} at {embedding_settings.ollama_base_url} ...")
    try:
        vectors = embed_texts([chunk.embedding_input for chunk in chunks])
    except EmbeddingError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    store_chunks(chunks, vectors)
    verify_store(expected_rows=len(chunks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
