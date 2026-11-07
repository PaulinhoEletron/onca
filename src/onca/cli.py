"""Interface de linha de comando: `onca ...`."""

import argparse
import sys
from importlib.metadata import version

import psycopg

from onca.config import get_settings

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="onca", description="Onça Guardiã")
    parser.add_argument("--version", action="version", version=f"onca {version('onca')}")
    sub = parser.add_subparsers(dest="command")
    db = sub.add_parser("db", help="comandos do banco de dados")
    db_sub = db.add_subparsers(dest="db_command", required=True)
    db_sub.add_parser("ping", help="testa a conexão e a extensão pgvector")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "db" and args.db_command == "ping":
        return db_ping()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
