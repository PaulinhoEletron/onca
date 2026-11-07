"""Extração de texto de PDF e HTML, com normalização leve."""

import logging
import re
from pathlib import Path

import trafilatura
from pypdf import PdfReader
from pypdf.errors import PyPdfError

logging.getLogger("pypdf").setLevel(logging.ERROR)

_META_CHARSET_RE = re.compile(rb"""charset\s*=\s*["']?\s*([A-Za-z0-9_\-]+)""", re.IGNORECASE)
_HYPHEN_BREAK_RE = re.compile(r"(\w)-\n(?=[a-zà-ÿ])")
_PARA_START_RE = re.compile(r"^(?:[A-ZÀ-Ý0-9§“\"(]|Art\.)")
_SENTENCE_END_RE = re.compile(r"[.!?:;]$")
# Ligaduras tipográficas de PDFs (ex.: "deﬁnidos") viram letras simples.
_LIGATURES = str.maketrans(
    {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st"}
)


class ExtractError(ValueError):
    """Não foi possível extrair texto do arquivo."""


def decode_html(raw: bytes) -> str:
    """Decodifica HTML: UTF-8 se válido, senão o charset declarado, senão Windows-1252."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass
    match = _META_CHARSET_RE.search(raw[:4096])
    declared = match.group(1).decode("ascii", "ignore") if match else ""
    for encoding in (declared, "cp1252"):
        if not encoding:
            continue
        try:
            return raw.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("latin-1")


def normalize_text(text: str) -> str:
    """Remove hifenização de fim de linha e espaços repetidos; parágrafos ficam separados
    por uma linha em branco."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    text = text.replace("­", "").replace("\x00", "").translate(_LIGATURES)
    text = _HYPHEN_BREAK_RE.sub(r"\1", text)
    paragraphs = [" ".join(line.split()) for line in re.split(r"\n\s*\n", text)]
    return "\n\n".join(p for p in paragraphs if p)


def _join_pdf_lines(page_text: str) -> str:
    """Une as linhas de um PDF em parágrafos: quebra só depois de frase terminada
    e antes de início de frase."""
    page_text = _HYPHEN_BREAK_RE.sub(r"\1", page_text)
    out: list[str] = []
    for line in page_text.splitlines():
        line = " ".join(line.split())
        if not line:
            out.append("")
        elif out and out[-1]:
            prev = out[-1]
            if _SENTENCE_END_RE.search(prev) and _PARA_START_RE.match(line):
                out.append("")
                out.append(line)
            else:
                out[-1] = f"{prev} {line}"
        else:
            out.append(line)
    return "\n".join(out)


def extract_pdf(path: Path) -> str:
    try:
        reader = PdfReader(path)
        pages = [_join_pdf_lines(page.extract_text() or "") for page in reader.pages]
    except (PyPdfError, OSError, ValueError, KeyError) as exc:
        raise ExtractError(f"PDF ilegível ({path.name}): {exc}") from exc
    return normalize_text("\n\n".join(pages))


def extract_html(path: Path) -> str:
    html = decode_html(path.read_bytes())
    text = trafilatura.extract(html, include_comments=False, include_tables=True, favor_recall=True)
    if not text:
        raise ExtractError(f"nenhum texto extraído do HTML ({path.name})")
    # o trafilatura separa os parágrafos com uma única quebra de linha
    return normalize_text(text.replace("\n", "\n\n"))


def extract_text(path: Path, kind: str) -> str:
    if kind == "pdf":
        text = extract_pdf(path)
    elif kind == "html":
        text = extract_html(path)
    else:
        raise ExtractError(f"tipo desconhecido: {kind}")
    if not text.strip():
        raise ExtractError(f"nenhum texto extraído de {path.name}")
    return text
