"""Ingestão da base de conhecimento: baixa, extrai, divide em chunks, gera embeddings e grava."""

import hashlib
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx
import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb

from onca.kb.download import DownloadError, download
from onca.kb.extract import ExtractError, extract_text
from onca.kb.sources import Source
from onca.rag.chunking import chunk_text
from onca.rag.embeddings import Embedder

Fetcher = Callable[[str, Path], Path]


@dataclass(frozen=True)
class SourceResult:
    title: str
    status: str  # "added" | "skipped" | "error"
    chunks: int = 0
    detail: str = ""


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _url_stored(conn: psycopg.Connection, url: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM documents WHERE kind = 'guideline' AND url = %s LIMIT 1", (url,)
    ).fetchone()
    return row is not None


def _store(
    conn: psycopg.Connection,
    source: Source,
    content_hash: str,
    chunks: list[str],
    vectors: list[list[float]],
    replace: bool,
) -> int | None:
    """Grava documento e chunks numa única transação. Devolve o nº de chunks, ou None
    se o conteúdo já existia."""
    with conn.transaction():
        if replace:
            conn.execute(
                "DELETE FROM documents "
                "WHERE kind = 'guideline' AND url = %s AND content_hash <> %s",
                (source.url, content_hash),
            )
        row = conn.execute(
            "INSERT INTO documents (source, url, title, kind, content_hash, metadata) "
            "VALUES (%s, %s, %s, 'guideline', %s, %s) "
            "ON CONFLICT (content_hash) DO NOTHING RETURNING id",
            (
                source.issuer,
                source.url,
                source.title,
                content_hash,
                Jsonb({"type": source.type, "chunks": len(chunks)}),
            ),
        ).fetchone()
        if row is None:
            return None
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (document_id, position, text, embedding) "
                "VALUES (%s, %s, %s, %s)",
                [
                    (row[0], i, text, Vector(vec))
                    for i, (text, vec) in enumerate(zip(chunks, vectors, strict=True))
                ],
            )
    return len(chunks)


def ingest_source(
    conn: psycopg.Connection,
    source: Source,
    embedder: Embedder,
    fetch: Fetcher | None = None,
    force: bool = False,
) -> SourceResult:
    if not force and _url_stored(conn, source.url):
        return SourceResult(source.title, "skipped", detail="mesma URL já carregada")
    with tempfile.TemporaryDirectory(prefix="onca-kb-") as tmp:
        path = (fetch or download)(source.url, Path(tmp) / f"source.{source.type}")
        text = extract_text(path, source.type)
    content_hash = _hash(text)
    exists = conn.execute(
        "SELECT 1 FROM documents WHERE content_hash = %s", (content_hash,)
    ).fetchone()
    if exists:
        return SourceResult(source.title, "skipped", detail="mesmo conteúdo já carregado")
    chunks = chunk_text(text, count=embedder.count_tokens)
    if not chunks:
        raise ExtractError("o texto não gerou nenhum trecho")
    vectors = embedder.embed_passages(chunks)
    stored = _store(conn, source, content_hash, chunks, vectors, replace=force)
    if stored is None:
        return SourceResult(source.title, "skipped", detail="mesmo conteúdo já carregado")
    return SourceResult(source.title, "added", chunks=stored)


def ingest_sources(
    conn: psycopg.Connection,
    sources: list[Source],
    embedder: Embedder,
    fetch: Fetcher | None = None,
    force: bool = False,
    on_result: Callable[[SourceResult], None] | None = None,
) -> list[SourceResult]:
    """Processa cada fonte de forma independente: uma falha não interrompe as demais."""
    register_vector(conn)
    results: list[SourceResult] = []
    for source in sources:
        try:
            result = ingest_source(conn, source, embedder, fetch, force)
        except (DownloadError, ExtractError, httpx.HTTPError, OSError, psycopg.Error) as exc:
            result = SourceResult(source.title, "error", detail=str(exc).strip()[:300])
        results.append(result)
        if on_result:
            on_result(result)
    return results
