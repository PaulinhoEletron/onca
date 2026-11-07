"""Conexão com o Postgres."""

import psycopg

from onca.config import get_settings

CONNECT_TIMEOUT = 5


def connect() -> psycopg.Connection:
    """Abre uma conexão usando DATABASE_URL (sem autocommit)."""
    return psycopg.connect(get_settings().database_url, connect_timeout=CONNECT_TIMEOUT)
