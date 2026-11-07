from collections.abc import Iterator

import psycopg
import pytest

from onca.cli import main
from onca.db.migrate import load_migrations
from onca.geo.data import read_municipalities
from onca.geo.lookup import find_region

pytestmark = pytest.mark.db


@pytest.fixture
def conn(db_url: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(db_url, autocommit=True) as c:
        c.execute("DROP SCHEMA public CASCADE")
        c.execute("CREATE SCHEMA public")
        yield c


def test_migrate_twice_is_idempotent(
    conn: psycopg.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["db", "migrate"]) == 0
    first = capsys.readouterr().out
    assert "aplicada: 0001_schema" in first
    assert main(["db", "migrate"]) == 0
    assert capsys.readouterr().out.strip() == "nada a aplicar"
    names = [r[0] for r in conn.execute("SELECT name FROM schema_migrations ORDER BY name")]
    assert names == [m.name for m in load_migrations()]
    count = conn.execute("SELECT count(*) FROM municipalities").fetchone()
    assert count is not None
    assert count[0] == len(read_municipalities())
    assert conn.execute("SELECT count(*) FROM states").fetchone() == (27,)
    assert conn.execute("SELECT count(*) FROM regions").fetchone() == (5,)


def test_tables_and_constraints(conn: psycopg.Connection) -> None:
    assert main(["db", "migrate"]) == 0
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO documents (source, url, title, kind, content_hash) "
            "VALUES ('s', 'u', 't', 'blog', 'h')"
        )
    conn.execute(
        "INSERT INTO documents (source, url, title, kind, content_hash) "
        "VALUES ('s', 'u', 't', 'news', 'h')"
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(
            "INSERT INTO documents (source, url, title, kind, content_hash) "
            "VALUES ('s2', 'u2', 't2', 'guideline', 'h')"
        )
    vec = "[" + ",".join(["0.1"] * 384) + "]"
    conn.execute(
        "INSERT INTO chunks (document_id, text, embedding) "
        "SELECT id, 'x', %s::vector FROM documents",
        (vec,),
    )
    conn.execute("DELETE FROM documents")
    assert conn.execute("SELECT count(*) FROM chunks").fetchone() == (0,)


def test_region_lookup(conn: psycopg.Connection) -> None:
    assert main(["db", "migrate"]) == 0
    assert [(m.uf, m.region) for m in find_region(conn, "Altamira")] == [("PA", "Norte")]
    assert [(m.uf, m.region) for m in find_region(conn, "são paulo")] == [("SP", "Sudeste")]
    assert [(m.uf, m.region) for m in find_region(conn, "SAO PAULO")] == [("SP", "Sudeste")]
    assert [(m.uf, m.region) for m in find_region(conn, "pa")] == [("PA", "Norte")]
    assert [(m.uf, m.region) for m in find_region(conn, "Pará")] == [("PA", "Norte")]
    assert find_region(conn, "Inexistente") == []
    assert find_region(conn, "   ") == []


def test_ambiguous_name(conn: psycopg.Connection, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["db", "migrate"]) == 0
    capsys.readouterr()
    matches = find_region(conn, "Bom Jesus")
    assert len(matches) > 1
    assert len({m.uf for m in matches}) > 1
    assert main(["geo", "region", "bom jesus"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == len(matches)
    assert all(" / " in line and "(Bom Jesus" in line for line in lines)


def test_cli_region_output_and_not_found(
    conn: psycopg.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["db", "migrate"]) == 0
    capsys.readouterr()
    assert main(["geo", "region", "Altamira"]) == 0
    assert capsys.readouterr().out.strip() == "PA / Norte"
    assert main(["geo", "region", "PA"]) == 0
    assert capsys.readouterr().out.strip() == "PA / Norte"
    assert main(["geo", "region", "Inexistente"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "não encontrado" in captured.err
