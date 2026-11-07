from pathlib import Path

import pytest

from onca.config import Settings


def test_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    for key in ("DATABASE_URL", "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(key, raising=False)
    s = Settings()
    assert "localhost:5433" in s.database_url
    assert s.llm_base_url is None
    assert s.llm_api_key is None
    assert s.llm_model is None


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:y@host:1/z")
    monkeypatch.setenv("LLM_MODEL", "modelo")
    s = Settings()
    assert s.database_url == "postgresql://x:y@host:1/z"
    assert s.llm_model == "modelo"
