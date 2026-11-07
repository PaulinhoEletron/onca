import psycopg
import pytest

from onca.cli import main
from onca.config import get_settings


@pytest.fixture
def db_url() -> str:
    url = get_settings().database_url
    try:
        psycopg.connect(url, connect_timeout=3).close()
    except psycopg.Error:
        pytest.skip("banco de dados indisponível")
    return url


@pytest.mark.db
def test_db_ping(db_url: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["db", "ping"]) == 0
    out = capsys.readouterr().out
    assert "ok" in out
    assert "pgvector" in out
