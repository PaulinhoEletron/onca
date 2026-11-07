"""Normalização de nomes para busca sem acentos e sem diferença de maiúsculas."""

import unicodedata


def normalize(text: str) -> str:
    """Remove acentos, ignora maiúsculas e colapsa espaços."""
    text = text.replace("’", "'").replace("‘", "'")
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(stripped.casefold().split())
