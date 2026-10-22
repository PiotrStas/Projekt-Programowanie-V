"""Testy rdzenia: rejestr, validate(), available_targets(), execute()."""

from pathlib import Path

import pytest

from konwerter.core import ConversionRequest, available_targets, execute, normalize, safe_path, supported_pairs
from konwerter.errors import ConversionError, InvalidInputError, OutputError, UnsupportedConversionError

DANE = Path(__file__).resolve().parent.parent / "dane_testowe"


def test_normalize():
    assert normalize(".CSV ") == "csv"


def test_rejestr_zawiera_grupe_a():
    assert ("csv", "json") in supported_pairs()
    assert ("json", "csv") in supported_pairs()


def test_available_targets():
    assert available_targets(Path("x.CSV")) == ["json"]
    assert available_targets(Path("x.json")) == ["csv"]
    assert available_targets(Path("x.exe")) == []
    assert available_targets(Path("bez_rozszerzenia")) == []


def test_validate_brak_pliku(tmp_path):
    req = ConversionRequest(tmp_path / "nie_ma.csv", "json", tmp_path)
    with pytest.raises(InvalidInputError, match="Nie znaleziono pliku"):
        req.validate()


def test_validate_brak_katalogu(tmp_path):
    req = ConversionRequest(DANE / "studenci.csv", "json", tmp_path / "nie_ma")
    with pytest.raises(OutputError, match="katalogu"):
        req.validate()


@pytest.mark.parametrize("fmt", ["pdf", "csv", ""])
def test_validate_nieobslugiwana_para(tmp_path, fmt):
    req = ConversionRequest(DANE / "studenci.csv", fmt, tmp_path)
    with pytest.raises(UnsupportedConversionError):
        req.validate()


def test_execute_tworzy_plik(tmp_path):
    wynik = execute(ConversionRequest(DANE / "studenci.csv", "json", tmp_path))
    assert wynik == tmp_path / "studenci.json"
    assert wynik.is_file()


def test_execute_nie_nadpisuje_bez_zgody(tmp_path):
    istniejacy = tmp_path / "studenci.json"
    istniejacy.write_text("NIE RUSZAĆ", encoding="utf-8")

    wynik = execute(ConversionRequest(DANE / "studenci.csv", "json", tmp_path))

    assert wynik.name == "studenci (1).json"
    assert istniejacy.read_text(encoding="utf-8") == "NIE RUSZAĆ"


def test_execute_nadpisuje_za_zgoda(tmp_path):
    istniejacy = tmp_path / "studenci.json"
    istniejacy.write_text("stare", encoding="utf-8")
    wynik = execute(ConversionRequest(DANE / "studenci.csv", "json", tmp_path, overwrite=True))
    assert wynik == istniejacy
    assert "Żółkiewski" in istniejacy.read_text(encoding="utf-8")


def test_execute_bledny_plik_nie_zostawia_smieci(tmp_path):
    with pytest.raises(ConversionError):
        execute(ConversionRequest(DANE / "bledny.json", "csv", tmp_path))
    assert list(tmp_path.iterdir()) == []  # ani wyniku, ani pliku .part


def test_safe_path(tmp_path):
    p = tmp_path / "a.json"
    assert safe_path(p) == p
    p.touch()
    (tmp_path / "a (1).json").touch()
    assert safe_path(p).name == "a (2).json"
