"""Wczytywanie CSV: separatory i kontrolowane błędy."""

import pytest

from studio.errors import DataLoadError
from studio.loader import detect_separator, load_csv


@pytest.mark.parametrize("plik, separator", [("test_01_przecinek.csv", ","), ("test_02_srednik.csv", ";")])
def test_przecinek_i_srednik(dane, plik, separator):
    df, sep = load_csv(dane / plik)
    assert sep == separator
    assert list(df.columns) == ["id", "value", "group"]
    assert df.shape == (3, 3)
    assert df["value"].tolist() == [10, 20, 30]


@pytest.mark.parametrize("linia, oczekiwany", [("a,b,c", ","), ("a;b;c", ";"), ("a\tb", "\t"), ("jedna", ",")])
def test_detect_separator(linia, oczekiwany):
    assert detect_separator(linia) == oczekiwany


def test_wadliwy_wiersz(dane):
    with pytest.raises(DataLoadError, match="Wadliwy wiersz 3") as info:
        load_csv(dane / "test_05_bledne_wiersze.csv")
    assert info.value.hint


def test_zle_kodowanie(tmp_path):
    plik = tmp_path / "ansi.csv"
    plik.write_text("miasto,ludnosc\nŁódź,670000\n", encoding="cp1250")
    with pytest.raises(DataLoadError, match="UTF-8"):
        load_csv(plik)


def test_utf8_z_bom(tmp_path):
    plik = tmp_path / "bom.csv"
    plik.write_text("miasto;ludnosc\nŁódź;670000\n", encoding="utf-8-sig")
    df, _ = load_csv(plik)
    assert list(df.columns) == ["miasto", "ludnosc"]
    assert df.loc[0, "miasto"] == "Łódź"


@pytest.mark.parametrize("tresc, fragment", [
    ("", "pusty"),
    ("id,value\n", "nie zawiera rekordów"),
    ("id,id\n1,2\n", "Powtórzone"),
])
def test_puste_i_bledne_pliki(tmp_path, tresc, fragment):
    plik = tmp_path / "x.csv"
    plik.write_text(tresc, encoding="utf-8")
    with pytest.raises(DataLoadError, match=fragment):
        load_csv(plik)


def test_brak_pliku(tmp_path):
    with pytest.raises(DataLoadError, match="Nie znaleziono"):
        load_csv(tmp_path / "nie_ma.csv")
