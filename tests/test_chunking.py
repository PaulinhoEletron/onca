from onca.rag.chunking import approx_tokens, chunk_text


def words(n: int, prefix: str = "w") -> str:
    return " ".join(f"{prefix}{i}" for i in range(n))


def count_words(text: str) -> int:
    return len(text.split())


def test_empty_and_whitespace() -> None:
    assert chunk_text("") == []
    assert chunk_text("  \n\n \n ") == []


def test_small_paragraphs_merge_into_one_chunk() -> None:
    text = "Primeiro parágrafo.\n\nSegundo parágrafo.\n\n\nTerceiro."
    chunks = chunk_text(text, count_words, max_tokens=50, overlap_tokens=5)
    assert chunks == ["Primeiro parágrafo.\n\nSegundo parágrafo.\n\nTerceiro."]


def test_chunks_respect_max_and_overlap() -> None:
    text = "\n\n".join(words(30, f"p{i}_") for i in range(10))
    chunks = chunk_text(text, count_words, max_tokens=70, overlap_tokens=10)
    assert len(chunks) > 1
    assert all(count_words(c) <= 70 for c in chunks)
    for prev, nxt in zip(chunks, chunks[1:], strict=False):
        tail = prev.split()[-5:]
        assert nxt.split()[:10] and " ".join(tail) in " ".join(nxt.split()[:10])


def test_long_paragraph_split_by_sentence() -> None:
    sentences = [f"{words(20, f's{i}_')}." for i in range(12)]
    chunks = chunk_text(" ".join(sentences), count_words, max_tokens=60, overlap_tokens=0)
    assert len(chunks) >= 4
    assert all(count_words(c) <= 60 for c in chunks)
    assert all(c.endswith(".") for c in chunks)


def test_sentence_without_punctuation_split_by_words() -> None:
    chunks = chunk_text(words(200), count_words, max_tokens=50, overlap_tokens=5)
    assert all(count_words(c) <= 50 for c in chunks)
    assert chunks[0].split()[0] == "w0"
    assert chunks[-1].split()[-1] == "w199"


def test_no_overlap_means_no_repetition() -> None:
    chunks = chunk_text(words(100), count_words, max_tokens=30, overlap_tokens=0)
    assert " ".join(chunks).split() == words(100).split()


def test_approx_tokens_default() -> None:
    assert approx_tokens("") == 0
    chunks = chunk_text("a" * 5000, max_tokens=100, overlap_tokens=10)
    assert chunks
