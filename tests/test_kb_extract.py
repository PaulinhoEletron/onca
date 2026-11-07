from pathlib import Path

import pytest

from onca.kb.extract import ExtractError, extract_text, normalize_text

FIXTURES = Path(__file__).parent / "fixtures"


def test_pdf_extraction_keeps_accents_and_joins_lines() -> None:
    text = extract_text(FIXTURES / "tiny.pdf", "pdf")
    assert "RESOLUÇÃO Nº 1" in text
    assert "limite de material particulado é fixado em 50 microgramas" in text
    assert "Art. 2º" in text.split("\n\n")[-1]


def test_html_latin1_decoded_correctly() -> None:
    text = extract_text(FIXTURES / "lei_latin1.html", "html")
    assert "incêndios florestais" in text
    assert "áreas de preservação permanente" in text
    assert "Art. 4º O uso do fogo" in text
    assert "�" not in text


def test_html_cp1252_without_declared_charset(tmp_path: Path) -> None:
    path = tmp_path / "a.html"
    path.write_bytes(
        "<html><body><p>Proteção da “vegetação” nativa e das águas.</p></body></html>".encode(
            "cp1252"
        )
    )
    assert "Proteção da “vegetação” nativa" in extract_text(path, "html")


def test_invalid_inputs(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(ExtractError):
        extract_text(bad, "pdf")
    empty = tmp_path / "e.html"
    empty.write_text("<html><body></body></html>")
    with pytest.raises(ExtractError):
        extract_text(empty, "html")
    with pytest.raises(ExtractError):
        extract_text(empty, "docx")


def test_normalize_text() -> None:
    assert normalize_text("uma pala-\nvra   com\xa0espaços\n\n\n\nnovo   parágrafo") == (
        "uma palavra com espaços\n\nnovo parágrafo"
    )


def test_normalize_text_expands_ligatures() -> None:
    assert normalize_text("valores deﬁnidos e ﬂuxo") == "valores definidos e fluxo"
