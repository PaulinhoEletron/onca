"""Divide textos em trechos (chunks) por parágrafo, com sobreposição."""

import math
import re
from collections.abc import Callable

TokenCounter = Callable[[str], int]

MAX_TOKENS = 450
OVERLAP_TOKENS = 50

_PARAGRAPH_RE = re.compile(r"\n\s*\n")
_SENTENCE_RE = re.compile(r"(?<=[.!?;:])\s+")


def approx_tokens(text: str) -> int:
    """Estimativa grosseira de tokens, para quando não há o tokenizer do modelo."""
    return math.ceil(len(text) / 3.5)


def _split_words(text: str, max_tokens: int, count: TokenCounter) -> list[str]:
    """Último recurso: quebra um texto sem pontuação em grupos de palavras."""
    pieces: list[str] = []
    current: list[str] = []
    for word in text.split():
        if current and count(" ".join([*current, word])) > max_tokens:
            pieces.append(" ".join(current))
            current = []
        current.append(word)
    if current:
        pieces.append(" ".join(current))
    return pieces


def _units(text: str, max_tokens: int, count: TokenCounter) -> list[str]:
    """Parágrafos; os grandes demais viram frases; as frases grandes viram grupos de palavras."""
    units: list[str] = []
    for raw in _PARAGRAPH_RE.split(text):
        para = " ".join(raw.split())
        if not para:
            continue
        if count(para) <= max_tokens:
            units.append(para)
            continue
        for sentence in _SENTENCE_RE.split(para):
            if count(sentence) <= max_tokens:
                units.append(sentence)
            else:
                units.extend(_split_words(sentence, max_tokens, count))
    return units


def _tail(text: str, overlap_tokens: int, count: TokenCounter) -> str:
    """Últimas palavras de `text` que cabem em `overlap_tokens`."""
    if overlap_tokens <= 0:
        return ""
    words = text.split()
    tail: list[str] = []
    for word in reversed(words):
        if count(" ".join([word, *tail])) > overlap_tokens:
            break
        tail.insert(0, word)
    return " ".join(tail)


def chunk_text(
    text: str,
    count: TokenCounter = approx_tokens,
    max_tokens: int = MAX_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[str]:
    """Junta parágrafos pequenos até ~`max_tokens`; cada trecho repete o fim do anterior."""
    chunks: list[str] = []
    current: list[str] = []  # unidades do trecho em construção (sem a sobreposição)
    overlap = ""
    for unit in _units(text, max_tokens, count):
        candidate = "\n\n".join([overlap, *current, unit] if overlap else [*current, unit])
        if count(candidate) <= max_tokens:
            current.append(unit)
            continue
        if current:
            chunk = "\n\n".join([overlap, *current] if overlap else current)
            chunks.append(chunk)
            overlap = _tail(chunk, overlap_tokens, count)
            current = []
            if overlap and count("\n\n".join([overlap, unit])) > max_tokens:
                overlap = ""
        elif overlap:  # a sobreposição sozinha impede a unidade de caber
            overlap = ""
        current.append(unit)
    if current:
        chunks.append("\n\n".join([overlap, *current] if overlap else current))
    return [c.strip() for c in chunks if c.strip()]
