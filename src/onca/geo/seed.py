"""Carga idempotente de estados e municípios a partir dos CSVs do IBGE."""

import psycopg

from onca.geo.data import read_municipalities, read_states
from onca.geo.normalize import normalize


def seed_geo(conn: psycopg.Connection) -> int:
    """Insere estados e municípios que ainda não existem. Devolve quantas linhas entraram."""
    inserted = 0
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO states (uf, name, name_norm, region_id) "
            "SELECT %s, %s, %s, id FROM regions WHERE name = %s "
            "ON CONFLICT DO NOTHING",
            [(s.uf, s.name, normalize(s.name), s.region) for s in read_states()],
        )
        inserted += max(cur.rowcount, 0)
        cur.executemany(
            "INSERT INTO municipalities (ibge_code, name, name_norm, uf) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
            [(m.ibge_code, m.name, normalize(m.name), m.uf) for m in read_municipalities()],
        )
        inserted += max(cur.rowcount, 0)
    return inserted
