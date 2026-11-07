"""Leitura e validação de `kb/sources.yaml`."""

from dataclasses import dataclass
from pathlib import Path

import yaml

VALID_TYPES = ("pdf", "html")
DEFAULT_SOURCES_PATH = Path(__file__).resolve().parents[3] / "kb" / "sources.yaml"


class SourcesError(ValueError):
    """O arquivo de fontes está malformado."""


@dataclass(frozen=True)
class Source:
    title: str
    url: str
    issuer: str
    type: str


def load_sources(path: Path = DEFAULT_SOURCES_PATH) -> list[Source]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SourcesError(f"não foi possível ler {path}: {exc}") from exc
    entries = data.get("sources") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        raise SourcesError(f"{path}: esperava uma lista não vazia em 'sources'")
    sources: list[Source] = []
    seen: set[str] = set()
    for i, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise SourcesError(f"{path}: entrada {i} não é um mapa")
        values: dict[str, str] = {}
        for key in ("title", "url", "issuer", "type"):
            value = entry.get(key)
            if not isinstance(value, str) or not value.strip():
                raise SourcesError(f"{path}: entrada {i} sem o campo '{key}'")
            values[key] = value.strip()
        if values["type"] not in VALID_TYPES:
            raise SourcesError(
                f"{path}: entrada {i} com type inválido '{values['type']}' "
                f"(use {' ou '.join(VALID_TYPES)})"
            )
        if not values["url"].startswith(("http://", "https://")):
            raise SourcesError(f"{path}: entrada {i} com URL inválida '{values['url']}'")
        if values["url"] in seen:
            raise SourcesError(f"{path}: URL repetida '{values['url']}'")
        seen.add(values["url"])
        sources.append(Source(**values))
    return sources
