import pytest

from onca.cli import main


@pytest.mark.db
def test_db_ping(db_url: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["db", "ping"]) == 0
    out = capsys.readouterr().out
    assert "ok" in out
    assert "pgvector" in out
