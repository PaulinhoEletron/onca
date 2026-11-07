"""Executor de migrações SQL simples, aplicadas em ordem e registradas no banco."""

from dataclasses import dataclass
from importlib import resources

import psycopg

from onca.geo.seed import seed_geo

# Chave do advisory lock que serializa execuções concorrentes de `migrate`.
LOCK_KEY = 7_262_024_001


@dataclass(frozen=True)
class Migration:
    name: str
    sql: str


@dataclass(frozen=True)
class MigrateResult:
    applied: list[str]
    seeded: int


def load_migrations() -> list[Migration]:
    """Lê os arquivos NNNN_nome.sql do pacote, ordenados pelo nome."""
    folder = resources.files("onca.db").joinpath("migrations")
    files = sorted((f for f in folder.iterdir() if f.name.endswith(".sql")), key=lambda f: f.name)
    return [Migration(f.name.removesuffix(".sql"), f.read_text(encoding="utf-8")) for f in files]


def migrate(conn: psycopg.Connection) -> MigrateResult:
    """Aplica as migrações pendentes e carrega os dados geográficos."""
    applied: list[str] = []
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_KEY,))
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
    for migration in load_migrations():
        with conn.transaction():
            # O lock é por transação: cada migração o retoma antes de checar o estado.
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_KEY,))
            done = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE name = %s", (migration.name,)
            ).fetchone()
            if done:
                continue
            conn.execute(migration.sql.encode())
            conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (migration.name,))
            applied.append(migration.name)
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_KEY,))
        seeded = seed_geo(conn)
    return MigrateResult(applied, seeded)
