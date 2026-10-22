"""Testy konwerterów CSV <-> JSON (Grupa A)."""

import csv
import json
from pathlib import Path

import pytest

from konwerter.converters.structured import csv_to_json, detect_delimiter, json_to_csv
from konwerter.errors import InvalidInputError

DANE = Path(__file__).resolve().parent.parent / "dane_testowe"


def write(path: Path, text: str, encoding: str = "utf-8") -> Path:
    path.write_text(text, encoding=encoding, newline="")
    return path


def read_csv(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


# ---------- CSV -> JSON ----------

def test_csv_to_json_polskie_znaki_puste_wartosci_i_cudzyslowy(tmp_path):
    out = tmp_path / "studenci.json"
    csv_to_json(DANE / "studenci.csv", out)
    data = json.loads(out.read_text(encoding="utf-8"))

    assert len(data) == 3
    assert list(data[0]) == ["nr_albumu", "imię", "nazwisko", "miasto", "średnia", "uwagi"]
    assert data[0]["nazwisko"] == "Żółkiewski"
    assert data[0]["nr_albumu"] == "012345"          # wiodące zero zachowane
    assert data[1]["średnia"] == ""                  # pusta wartość zachowana
    assert data[1]["uwagi"] == "brak oceny; poprawka we wrześniu"  # separator w cudzysłowie
    assert data[2]["uwagi"] == 'cytat: "zdał"'
    assert "Żółkiewski" in out.read_text(encoding="utf-8")  # bez Ż... (ensure_ascii=False)


def test_csv_z_bom_i_przecinkiem(tmp_path):
    src = write(tmp_path / "a.csv", "﻿id,nazwa\r\n1,Łódź\r\n", encoding="utf-8")
    out = tmp_path / "a.json"
    csv_to_json(src, out)
    assert json.loads(out.read_text(encoding="utf-8")) == [{"id": "1", "nazwa": "Łódź"}]


def test_csv_pole_wieloliniowe(tmp_path):
    src = write(tmp_path / "a.csv", 'id,opis\n1,"linia 1\nlinia 2"\n')
    out = tmp_path / "a.json"
    csv_to_json(src, out)
    assert json.loads(out.read_text(encoding="utf-8"))[0]["opis"] == "linia 1\nlinia 2"


def test_csv_tylko_naglowek_daje_pusta_tablice(tmp_path):
    src = write(tmp_path / "a.csv", "id,nazwa\n")
    out = tmp_path / "a.json"
    csv_to_json(src, out)
    assert json.loads(out.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("linia, oczekiwany", [("a,b,c", ","), ("a;b;c", ";"), ("a\tb", "\t"), ("jedna", ",")])
def test_detect_delimiter(linia, oczekiwany):
    assert detect_delimiter(linia) == oczekiwany


def test_csv_zla_liczba_kolumn(tmp_path):
    with pytest.raises(InvalidInputError, match="Wiersz 3"):
        csv_to_json(DANE / "zla_liczba_kolumn.csv", tmp_path / "x.json")


@pytest.mark.parametrize("tresc, fragment", [
    ("", "pusty"),
    ("id,,cena\n1,2,3\n", "nie ma nazwy"),
    ("id,id\n1,2\n", "Powtórzone"),
])
def test_csv_bledne_dane(tmp_path, tresc, fragment):
    src = write(tmp_path / "a.csv", tresc)
    with pytest.raises(InvalidInputError, match=fragment):
        csv_to_json(src, tmp_path / "a.json")


def test_csv_nie_utf8(tmp_path):
    src = write(tmp_path / "a.csv", "miasto\nŁódź\n", encoding="cp1250")
    with pytest.raises(InvalidInputError, match="UTF-8"):
        csv_to_json(src, tmp_path / "a.json")


# ---------- JSON -> CSV ----------

def test_json_to_csv_kolumny_typy_i_brakujace_pola(tmp_path):
    out = tmp_path / "produkty.csv"
    json_to_csv(DANE / "produkty.json", out)
    rows = read_csv(out)

    assert rows[0] == ["id", "nazwa", "cena", "dostępny", "uwagi"]  # kolejność pierwszego wystąpienia
    assert rows[1] == ["1", "Długopis żelowy", "4.99", "true", ""]  # brak "uwagi" -> pusta komórka
    assert rows[2] == ["2", "Zeszyt A5, 60 kartek", "6.5", "false", ""]  # null -> pusta komórka
    assert rows[3][1] == "Gumka „Pelikan”"


def test_json_to_csv_zapisuje_bom_dla_excela(tmp_path):
    out = tmp_path / "p.csv"
    json_to_csv(DANE / "produkty.json", out)
    assert out.read_bytes().startswith(b"\xef\xbb\xbf")


def test_bledny_json_daje_kontrolowany_komunikat(tmp_path):
    with pytest.raises(InvalidInputError, match=r"Niepoprawny JSON.*wiersz 3"):
        json_to_csv(DANE / "bledny.json", tmp_path / "x.csv")


def test_zagniezdzony_json(tmp_path):
    with pytest.raises(InvalidInputError, match="zagnieżdżone"):
        json_to_csv(DANE / "zagniezdzony.json", tmp_path / "x.csv")


@pytest.mark.parametrize("tresc, fragment", [
    ("", "pusty"),
    ("[]", "pusta"),
    ('{"id": 1}', "pojedynczy obiekt"),
    ("42", "tablica obiektów"),
    ('[{"id": 1}, 5]', "Element nr 2"),
])
def test_json_zla_struktura(tmp_path, tresc, fragment):
    src = write(tmp_path / "a.json", tresc)
    with pytest.raises(InvalidInputError, match=fragment):
        json_to_csv(src, tmp_path / "a.csv")


# ---------- obie strony ----------

def test_round_trip_csv_json_csv(tmp_path):
    """Wyniki można ponownie odczytać: CSV -> JSON -> CSV daje te same dane."""
    j = tmp_path / "s.json"
    c = tmp_path / "s.csv"
    csv_to_json(DANE / "studenci.csv", j)
    json_to_csv(j, c)

    with (DANE / "studenci.csv").open(encoding="utf-8", newline="") as f:
        oryginal = list(csv.reader(f, delimiter=";"))
    assert read_csv(c) == oryginal
