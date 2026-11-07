from pathlib import Path

import pytest

from onca.kb.sources import DEFAULT_SOURCES_PATH, VALID_TYPES, SourcesError, load_sources


def test_default_sources_are_valid() -> None:
    sources = load_sources(DEFAULT_SOURCES_PATH)
    assert len(sources) >= 5
    assert len({s.url for s in sources}) == len(sources)
    assert all(s.title and s.issuer and s.type in VALID_TYPES for s in sources)
    assert all(s.url.startswith("https://") for s in sources)


def write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "s.yaml"
    path.write_text(body, encoding="utf-8")
    return path


ENTRY = "  - title: T\n    url: https://x.org/a\n    issuer: I\n    type: pdf\n"


def test_valid_file(tmp_path: Path) -> None:
    assert [s.title for s in load_sources(write(tmp_path, "sources:\n" + ENTRY))] == ["T"]


@pytest.mark.parametrize(
    "body",
    [
        "sources: []\n",
        "outra: 1\n",
        "sources:\n  - title: T\n    url: https://x.org\n    issuer: I\n",
        "sources:\n" + ENTRY.replace("pdf", "docx"),
        "sources:\n" + ENTRY.replace("https://x.org/a", "ftp://x"),
        "sources:\n" + ENTRY + ENTRY,
    ],
)
def test_invalid_files(tmp_path: Path, body: str) -> None:
    with pytest.raises(SourcesError):
        load_sources(write(tmp_path, body))


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(SourcesError):
        load_sources(tmp_path / "nada.yaml")
