import csv

import pytest

from onca.geo.data import MUNICIPALITIES_CSV, STATES_CSV, read_municipalities, read_states
from onca.geo.normalize import normalize

EXPECTED_REGION = {
    "AC": "Norte", "AM": "Norte", "AP": "Norte", "PA": "Norte", "RO": "Norte",
    "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste",
    "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MS": "Centro-Oeste", "MT": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}  # fmt: skip


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("São Paulo", "sao paulo"),
        ("  SAO   paulo ", "sao paulo"),
        ("Pará", "para"),
        ("Alta Floresta D’Oeste", "alta floresta d'oeste"),
        ("Mogi-Guaçu", "mogi-guacu"),
    ],
)
def test_normalize(text: str, expected: str) -> None:
    assert normalize(text) == expected


def test_all_27_ufs_mapped_to_right_region() -> None:
    states = read_states()
    assert len(states) == 27
    assert {s.uf: s.region for s in states} == EXPECTED_REGION
    assert len(EXPECTED_REGION) == 27


def test_five_regions() -> None:
    assert {s.region for s in read_states()} == {
        "Norte",
        "Nordeste",
        "Centro-Oeste",
        "Sudeste",
        "Sul",
    }


def test_municipalities_integrity() -> None:
    rows = read_municipalities()
    assert len(rows) == 5571  # 5570 municípios + Brasília (DF), como retorna a API do IBGE
    assert len({r.ibge_code for r in rows}) == len(rows)
    ufs = set(EXPECTED_REGION)
    assert {r.uf for r in rows} == ufs
    assert all(r.name.strip() for r in rows)


def test_csv_headers() -> None:
    with open(MUNICIPALITIES_CSV, encoding="utf-8") as f:
        assert next(csv.reader(f)) == ["ibge_code", "name", "uf"]
    with open(STATES_CSV, encoding="utf-8") as f:
        assert next(csv.reader(f)) == ["uf", "name", "region"]


def test_altamira_in_csv() -> None:
    assert [r.uf for r in read_municipalities() if normalize(r.name) == "altamira"] == ["PA"]
