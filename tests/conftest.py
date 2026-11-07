from collections.abc import Iterator

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from onca.config import get_settings

TEST_DB = "onca_test"


@pytest.fixture(scope="session")
def _test_db_url() -> str:
    """Cria (se preciso) um banco separado para os testes, sem tocar no banco de dev."""
    url = get_settings().database_url
    try:
        with psycopg.connect(url, connect_timeout=3, autocommit=True) as conn:
            exists = conn.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,)
            ).fetchone()
            if not exists:
                conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TEST_DB)))
    except psycopg.Error:
        pytest.skip("banco de dados indisponível")
    params = conninfo_to_dict(url)
    params["dbname"] = TEST_DB
    return make_conninfo(**params)


@pytest.fixture
def db_url(_test_db_url: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """URL do banco de testes; o CLI também passa a usá-lo via DATABASE_URL."""
    monkeypatch.setenv("DATABASE_URL", _test_db_url)
    yield _test_db_url
