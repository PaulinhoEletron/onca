"""Leitura dos CSVs do IBGE versionados em `data/`."""

import csv
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
MUNICIPALITIES_CSV = DATA_DIR / "ibge_municipios.csv"
STATES_CSV = DATA_DIR / "ibge_estados.csv"


@dataclass(frozen=True)
class StateRow:
    uf: str
    name: str
    region: str


@dataclass(frozen=True)
class MunicipalityRow:
    ibge_code: int
    name: str
    uf: str


def read_states(path: Path = STATES_CSV) -> list[StateRow]:
    with open(path, newline="", encoding="utf-8") as f:
        return [StateRow(r["uf"], r["name"], r["region"]) for r in csv.DictReader(f)]


def read_municipalities(path: Path = MUNICIPALITIES_CSV) -> list[MunicipalityRow]:
    with open(path, newline="", encoding="utf-8") as f:
        return [MunicipalityRow(int(r["ibge_code"]), r["name"], r["uf"]) for r in csv.DictReader(f)]
