"""Interface de linha de comando: `onca ...`."""

import argparse
import sys
from importlib.metadata import version
from pathlib import Path

import psycopg

from onca.config import get_settings
from onca.db.connection import connect
from onca.db.migrate import migrate
from onca.geo.lookup import find_region
from onca.kb.ingest import SourceResult, ingest_sources
from onca.kb.sources import DEFAULT_SOURCES_PATH, SourcesError, load_sources
from onca.rag.embeddings import get_embedder
from onca.rag.search import search_chunks

CONNECT_TIMEOUT = 5


def db_ping() -> int:
    url = get_settings().database_url
    try:
        with psycopg.connect(url, connect_timeout=CONNECT_TIMEOUT, autocommit=True) as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            row = conn.execute("SELECT version()").fetchone()
            ext = conn.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            ext_row = ext.fetchone()
    except psycopg.Error as exc:
        detail = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
        print(
            f"erro: não foi possível conectar ao banco de dados ({detail}). "
            "Verifique se ele está no ar (`make up`) e se DATABASE_URL está correta.",
            file=sys.stderr,
        )
        return 1
    pg_version = row[0] if row else "desconhecida"
    vector_version = ext_row[0] if ext_row else "desconhecida"
    print("ok")
    print(f"Postgres: {pg_version}")
    print(f"pgvector: {vector_version}")
    return 0


def _db_error(exc: psycopg.Error) -> None:
    detail = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
    print(
        f"erro: falha no banco de dados ({detail}). "
        "Verifique se ele está no ar (`make up`) e se DATABASE_URL está correta.",
        file=sys.stderr,
    )


def db_migrate() -> int:
    try:
        with connect() as conn:
            result = migrate(conn)
    except psycopg.Error as exc:
        _db_error(exc)
        return 1
    for name in result.applied:
        print(f"aplicada: {name}")
    if result.seeded:
        print(f"dados geográficos carregados: {result.seeded} linhas")
    if not result.applied and not result.seeded:
        print("nada a aplicar")
    return 0


def geo_region(query: str) -> int:
    try:
        with connect() as conn:
            matches = find_region(conn, query)
    except psycopg.Error as exc:
        _db_error(exc)
        return 1
    if not matches:
        print(
            f"erro: '{query}' não encontrado (município, UF ou estado). "
            "Rode `onca db migrate` se o banco ainda está vazio.",
            file=sys.stderr,
        )
        return 1
    for m in matches:
        line = f"{m.uf} / {m.region}"
        print(f"{line} ({m.municipality})" if m.municipality and len(matches) > 1 else line)
    return 0


def _print_result(result: SourceResult) -> None:
    if result.status == "added":
        print(f"  adicionado: {result.title} ({result.chunks} trechos)", flush=True)
    elif result.status == "skipped":
        print(f"  ignorado:   {result.title} ({result.detail})", flush=True)
    else:
        print(f"  erro:       {result.title} ({result.detail})", flush=True)


def kb_ingest(sources_path: Path, force: bool) -> int:
    try:
        sources = load_sources(sources_path)
    except SourcesError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    print(f"Carregando {len(sources)} documentos...")
    try:
        with connect() as conn:
            results = ingest_sources(
                conn, sources, get_embedder(), force=force, on_result=_print_result
            )
    except psycopg.Error as exc:
        _db_error(exc)
        return 1
    added = [r for r in results if r.status == "added"]
    skipped = [r for r in results if r.status == "skipped"]
    failed = [r for r in results if r.status == "error"]
    print(
        f"Resumo: {len(added)} adicionados ({sum(r.chunks for r in added)} trechos), "
        f"{len(skipped)} ignorados, {len(failed)} com erro."
    )
    return 1 if failed else 0


def kb_search(query: str, k: int) -> int:
    if not query.strip():
        print("erro: a pergunta está vazia.", file=sys.stderr)
        return 1
    if k < 1:
        print("erro: -k deve ser pelo menos 1.", file=sys.stderr)
        return 1
    try:
        with connect() as conn:
            hits = search_chunks(conn, get_embedder(), query, k)
    except psycopg.Error as exc:
        _db_error(exc)
        return 1
    if not hits:
        print("Nenhum trecho encontrado. Rode `onca kb ingest` para carregar a base.")
        return 0
    for rank, hit in enumerate(hits, start=1):
        excerpt = " ".join(hit.text.split())
        if len(excerpt) > 300:
            excerpt = excerpt[:300].rstrip() + "..."
        print(f"{rank}. [{hit.score:.3f}] {hit.title} — {hit.issuer}")
        print(f"   {hit.url}")
        print(f"   {excerpt}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="onca", description="Onça Guardiã")
    parser.add_argument("--version", action="version", version=f"onca {version('onca')}")
    sub = parser.add_subparsers(dest="command")
    db = sub.add_parser("db", help="comandos do banco de dados")
    db_sub = db.add_subparsers(dest="db_command", required=True)
    db_sub.add_parser("ping", help="testa a conexão e a extensão pgvector")
    db_sub.add_parser("migrate", help="aplica as migrações pendentes")
    geo = sub.add_parser("geo", help="consultas geográficas")
    geo_sub = geo.add_subparsers(dest="geo_command", required=True)
    region = geo_sub.add_parser("region", help="região de um município, UF ou estado")
    region.add_argument("name", help='ex.: "Altamira", "PA", "São Paulo"')
    kb = sub.add_parser("kb", help="base de conhecimento (documentos oficiais)")
    kb_sub = kb.add_subparsers(dest="kb_command", required=True)
    ingest = kb_sub.add_parser("ingest", help="baixa e carrega os documentos de kb/sources.yaml")
    ingest.add_argument("--sources", type=Path, default=DEFAULT_SOURCES_PATH, help="arquivo YAML")
    ingest.add_argument("--force", action="store_true", help="baixa de novo mesmo se já carregado")
    search = kb_sub.add_parser("search", help="busca trechos por similaridade")
    search.add_argument("query", help="pergunta em linguagem natural")
    search.add_argument("-k", type=int, default=5, help="número de resultados (padrão: 5)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "db" and args.db_command == "ping":
        return db_ping()
    if args.command == "db" and args.db_command == "migrate":
        return db_migrate()
    if args.command == "geo" and args.geo_command == "region":
        return geo_region(args.name)
    if args.command == "kb" and args.kb_command == "ingest":
        return kb_ingest(args.sources, args.force)
    if args.command == "kb" and args.kb_command == "search":
        return kb_search(args.query, args.k)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
