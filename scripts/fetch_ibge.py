"""Baixa municípios e estados do IBGE e regenera os CSVs em `data/`.

Uso: uv run python scripts/fetch_ibge.py
"""

import csv
import gzip
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TIMEOUT = 60
RETRIES = 4


def fetch() -> list[dict[str, Any]]:
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(URL, timeout=TIMEOUT) as resp:  # noqa: S310
                raw = resp.read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            data: list[dict[str, Any]] = json.loads(raw)
            return data
        except (urllib.error.URLError, TimeoutError):
            if attempt == RETRIES - 1:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("inalcançável")


def uf_of(item: dict[str, Any]) -> dict[str, Any]:
    micro = item.get("microrregiao")
    if micro:
        uf: dict[str, Any] = micro["mesorregiao"]["UF"]
        return uf
    uf = item["regiao-imediata"]["regiao-intermediaria"]["UF"]
    return uf


def main() -> None:
    items = fetch()
    municipalities: list[tuple[int, str, str]] = []
    states: dict[str, tuple[str, str]] = {}
    for item in items:
        uf = uf_of(item)
        municipalities.append((item["id"], item["nome"], uf["sigla"]))
        states[uf["sigla"]] = (uf["nome"], uf["regiao"]["nome"])
    municipalities.sort()
    DATA_DIR.mkdir(exist_ok=True)
    with open(DATA_DIR / "ibge_municipios.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ibge_code", "name", "uf"])
        w.writerows(municipalities)
    with open(DATA_DIR / "ibge_estados.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["uf", "name", "region"])
        for sigla in sorted(states):
            w.writerow([sigla, *states[sigla]])
    print(f"{len(municipalities)} municípios, {len(states)} estados")


if __name__ == "__main__":
    main()
