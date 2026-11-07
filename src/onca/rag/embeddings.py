"""Embeddings locais (multilingual-e5-small) com os prefixos `passage:` e `query:`."""

from functools import lru_cache
from typing import Any, Protocol

from onca.config import get_settings

EMBEDDING_DIM = 384
BATCH_SIZE = 32
PASSAGE_PREFIX = "passage: "
QUERY_PREFIX = "query: "


class Embedder(Protocol):
    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...

    def count_tokens(self, text: str) -> int: ...


class SentenceTransformerEmbedder:
    """Carrega o modelo na primeira chamada e o reutiliza no processo."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model: Any = None

    def _load(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            from transformers.utils import logging as hf_logging

            hf_logging.set_verbosity_error()  # o aviso de "sequência longa" é esperado ao medir
            self._model = SentenceTransformer(self.model_name, device="cpu")
        return self._model

    def _encode(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        vectors = model.encode(
            texts, batch_size=BATCH_SIZE, normalize_embeddings=True, show_progress_bar=False
        )
        return [[float(x) for x in v] for v in vectors]

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._encode([PASSAGE_PREFIX + t for t in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._encode([QUERY_PREFIX + text])[0]

    def count_tokens(self, text: str) -> int:
        tokenizer = self._load().tokenizer
        return len(tokenizer(text, add_special_tokens=False)["input_ids"])


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    return SentenceTransformerEmbedder(get_settings().embedding_model)
