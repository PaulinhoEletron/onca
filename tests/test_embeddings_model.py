"""Teste opcional com o modelo real: `uv run pytest -m model` (precisa do modelo em cache)."""

import os

import pytest

from onca.rag.embeddings import EMBEDDING_DIM, SentenceTransformerEmbedder

pytestmark = pytest.mark.model


def test_real_model_dimension_and_prefixes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    embedder = SentenceTransformerEmbedder("intfloat/multilingual-e5-small")
    try:
        embedder._load()
    except Exception as exc:  # modelo ausente do cache / offline
        pytest.skip(f"modelo não disponível localmente: {exc}")
    seen: list[list[str]] = []
    real_encode = embedder._model.encode

    def spy(texts: list[str], **kwargs: object) -> object:
        seen.append(list(texts))
        return real_encode(texts, **kwargs)

    monkeypatch.setattr(embedder._model, "encode", spy)
    passage = embedder.embed_passages(["limite de material particulado"])[0]
    query = embedder.embed_query("qualidade do ar")
    assert len(passage) == len(query) == EMBEDDING_DIM
    assert seen == [["passage: limite de material particulado"], ["query: qualidade do ar"]]
    assert abs(sum(x * x for x in query) - 1.0) < 1e-3
    assert embedder.count_tokens("qualidade do ar") > 0
