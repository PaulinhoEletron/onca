"""Busca semântica nos chunks (distância de cosseno do pgvector)."""

from dataclasses import dataclass

import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector

from onca.rag.embeddings import Embedder


@dataclass(frozen=True)
class Hit:
    score: float
    title: str
    issuer: str
    url: str
    position: int
    text: str


def search_chunks(
    conn: psycopg.Connection,
    embedder: Embedder,
    query: str,
    k: int = 5,
    kind: str = "guideline",
) -> list[Hit]:
    register_vector(conn)
    # Com filtro (kind), o HNSW continua a varredura até achar k linhas, na ordem exata.
    conn.execute("SET hnsw.iterative_scan = strict_order")
    vector = Vector(embedder.embed_query(query))
    rows = conn.execute(
        "SELECT 1 - (c.embedding <=> %(v)s) AS score, d.title, d.source, d.url, c.position, c.text "
        "FROM chunks c JOIN documents d ON d.id = c.document_id "
        "WHERE d.kind = %(kind)s AND c.embedding IS NOT NULL "
        "ORDER BY c.embedding <=> %(v)s LIMIT %(k)s",
        {"v": vector, "kind": kind, "k": k},
    ).fetchall()
    return [Hit(float(r[0]), r[1], r[2], r[3], r[4], r[5]) for r in rows]
