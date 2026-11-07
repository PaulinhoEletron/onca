"""Busca de região a partir do nome de um município, UF ou estado."""

from dataclasses import dataclass

import psycopg

from onca.geo.normalize import normalize


@dataclass(frozen=True)
class Match:
    uf: str
    region: str
    municipality: str | None = None


def find_region(conn: psycopg.Connection, query: str) -> list[Match]:
    """Procura por sigla de UF, nome de estado ou nome de município."""
    key = normalize(query)
    if not key:
        return []
    state_rows = conn.execute(
        "SELECT s.uf, r.name FROM states s JOIN regions r ON r.id = s.region_id "
        "WHERE lower(s.uf) = %s OR s.name_norm = %s",
        (key, key),
    ).fetchall()
    matches = [Match(uf=row[0], region=row[1]) for row in state_rows]
    muni_rows = conn.execute(
        "SELECT m.uf, r.name, m.name FROM municipalities m "
        "JOIN states s ON s.uf = m.uf JOIN regions r ON r.id = s.region_id "
        "WHERE m.name_norm = %s ORDER BY m.uf, m.name",
        (key,),
    ).fetchall()
    muni_matches = [Match(uf=row[0], region=row[1], municipality=row[2]) for row in muni_rows]
    # "São Paulo" é estado e município: não repete a mesma UF.
    muni_ufs = {m.uf for m in muni_matches}
    return [m for m in matches if m.uf not in muni_ufs] + muni_matches
