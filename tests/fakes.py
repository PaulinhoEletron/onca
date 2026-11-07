"""Embedder determinístico para testes (sem modelo e sem rede)."""

import hashlib
import math
import re

from onca.rag.embeddings import EMBEDDING_DIM


class FakeEmbedder:
    """Saco de palavras com hash em 384 dimensões, normalizado."""

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * EMBEDDING_DIM
        for word in re.findall(r"\w+", text.lower()):
            h = int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], "big")
            v[h % EMBEDDING_DIM] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)

    def count_tokens(self, text: str) -> int:
        return len(text.split())
