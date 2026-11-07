import shutil
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from fakes import FakeEmbedder

from onca.cli import main
from onca.db.migrate import migrate
from onca.kb.download import DownloadError
from onca.kb.ingest import ingest_sources
from onca.kb.sources import Source
from onca.rag.search import search_chunks

pytestmark = pytest.mark.db
FIXTURES = Path(__file__).parent / "fixtures"

PDF = Source("Resolução teste", "https://x.org/res.pdf", "CONAMA", "pdf")
HTML = Source("Lei teste", "https://x.org/lei.html", "Planalto", "html")
BAD = Source("Fonte quebrada", "https://x.org/quebrada.pdf", "Ninguém", "pdf")
FILES = {PDF.url: FIXTURES / "tiny.pdf", HTML.url: FIXTURES / "lei_latin1.html"}


def fake_fetch(url: str, dest: Path) -> Path:
    if url not in FILES:
        raise DownloadError(f"HTTP 404 em {url}")
    shutil.copy(FILES[url], dest)
    return dest


@pytest.fixture
def conn(db_url: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(db_url, autocommit=True) as c:
        c.execute("DROP SCHEMA public CASCADE")
        c.execute("CREATE SCHEMA public")
        migrate(c)
        yield c


def counts(conn: psycopg.Connection) -> tuple[int, int]:
    docs = conn.execute("SELECT count(*) FROM documents").fetchone()
    chunks = conn.execute("SELECT count(*) FROM chunks").fetchone()
    assert docs is not None and chunks is not None
    return docs[0], chunks[0]


def test_ingest_twice_second_adds_nothing(conn: psycopg.Connection) -> None:
    first = ingest_sources(conn, [PDF, HTML], FakeEmbedder(), fake_fetch)
    assert [r.status for r in first] == ["added", "added"]
    docs, chunks = counts(conn)
    assert docs == 2 and chunks == sum(r.chunks for r in first) > 0
    second = ingest_sources(conn, [PDF, HTML], FakeEmbedder(), fake_fetch)
    assert [r.status for r in second] == ["skipped", "skipped"]
    assert counts(conn) == (docs, chunks)


def test_second_run_skips_without_downloading(conn: psycopg.Connection) -> None:
    ingest_sources(conn, [PDF], FakeEmbedder(), fake_fetch)

    def no_fetch(url: str, dest: Path) -> Path:
        raise AssertionError("não deveria baixar")

    assert ingest_sources(conn, [PDF], FakeEmbedder(), no_fetch)[0].status == "skipped"


def test_force_redownloads_but_same_hash_adds_nothing(conn: psycopg.Connection) -> None:
    ingest_sources(conn, [PDF], FakeEmbedder(), fake_fetch)
    before = counts(conn)
    result = ingest_sources(conn, [PDF], FakeEmbedder(), fake_fetch, force=True)[0]
    assert result.status == "skipped"
    assert counts(conn) == before


def test_force_replaces_changed_content(conn: psycopg.Connection, tmp_path: Path) -> None:
    ingest_sources(conn, [HTML], FakeEmbedder(), fake_fetch)
    changed = tmp_path / "novo.html"
    changed.write_text(
        "<html><body><p>Texto totalmente novo sobre secas e enchentes.</p></body></html>"
    )

    def fetch_new(url: str, dest: Path) -> Path:
        shutil.copy(changed, dest)
        return dest

    assert ingest_sources(conn, [HTML], FakeEmbedder(), fetch_new, force=True)[0].status == "added"
    assert counts(conn)[0] == 1


def test_failing_source_does_not_stop_others(conn: psycopg.Connection) -> None:
    results = ingest_sources(conn, [BAD, PDF, HTML], FakeEmbedder(), fake_fetch)
    assert [r.status for r in results] == ["error", "added", "added"]
    assert "404" in results[0].detail
    assert counts(conn)[0] == 2


def test_search_returns_expected_chunk_first(conn: psycopg.Connection) -> None:
    ingest_sources(conn, [PDF, HTML], FakeEmbedder(), fake_fetch)
    hits = search_chunks(conn, FakeEmbedder(), "limite de material particulado", k=3)
    assert hits[0].title == "Resolução teste"
    assert "material particulado" in hits[0].text
    assert hits[0].score >= hits[-1].score
    hits = search_chunks(conn, FakeEmbedder(), "uso do fogo em áreas rurais", k=1)
    assert hits[0].title == "Lei teste"
    assert search_chunks(conn, FakeEmbedder(), "fogo", k=3, kind="news") == []


def test_cli_ingest_exit_code_and_search(
    conn: psycopg.Connection,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sources = tmp_path / "s.yaml"
    sources.write_text(
        "sources:\n"
        + "".join(
            f"  - title: {s.title}\n    url: {s.url}\n    issuer: {s.issuer}\n    type: {s.type}\n"
            for s in (PDF, BAD)
        )
    )
    monkeypatch.setattr("onca.cli.get_embedder", lambda: FakeEmbedder())
    monkeypatch.setattr("onca.kb.ingest.download", fake_fetch)
    assert main(["kb", "ingest", "--sources", str(sources)]) == 1
    out = capsys.readouterr().out
    assert "adicionado: Resolução teste" in out
    assert "erro:       Fonte quebrada" in out
    assert "1 adicionados" in out and "1 com erro" in out
    assert main(["kb", "search", "material particulado", "-k", "2"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("1. [") and "Resolução teste — CONAMA" in out
    assert main(["kb", "search", "  "]) == 1
    assert main(["kb", "search", "fogo", "-k", "0"]) == 1
