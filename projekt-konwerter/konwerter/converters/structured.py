"""Grupa A – dane strukturalne: CSV -> JSON i JSON -> CSV.

Ustalona semantyka (opisana też w README):

CSV (wejście)
- kodowanie UTF-8 (z BOM lub bez – BOM dodaje np. Excel),
- PIERWSZY wiersz to nagłówek; nazwy kolumn muszą być niepuste i unikalne,
- separator wykrywany automatycznie z nagłówka: przecinek, średnik albo tabulator,
- pola w cudzysłowach "..." mogą zawierać separator i znaki nowej linii,
- puste linie są pomijane; każdy wiersz musi mieć tyle pól, ile nagłówek,
- wartości NIE są zgadywane – wszystko trafia do JSON jako tekst ("007" zostaje "007").

JSON (wejście)
- tablica obiektów: [ {"kolumna": wartość, ...}, ... ],
- wartości proste: tekst, liczba, true/false, null; zagnieżdżone obiekty/listy -> błąd,
- obiekty mogą mieć różne klucze: kolumny = suma kluczy w kolejności pierwszego wystąpienia,
  brakujące pola -> pusta komórka.

CSV (wyjście): UTF-8 z BOM (Excel poprawnie pokaże polskie znaki), separator przecinek,
null -> pusta komórka, true/false -> "true"/"false".
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from ..core import converter
from ..errors import InvalidInputError
from .common import read_text_utf8 as _read_text

OUTPUT_CSV_ENCODING = "utf-8-sig"
OUTPUT_CSV_DELIMITER = ","
CANDIDATE_DELIMITERS = [",", ";", "\t"]


def detect_delimiter(header_line: str) -> str:
    """Wybiera separator, który najczęściej występuje w linii nagłówka.

    Prosta, przewidywalna heurystyka zamiast csv.Sniffer. Jeśli w nagłówku nie ma
    żadnego separatora, plik ma jedną kolumnę i używamy przecinka.
    """
    counts = {d: header_line.count(d) for d in CANDIDATE_DELIMITERS}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def _validate_header(header: list[str]) -> list[str]:
    header = [name.strip() for name in header]
    for i, name in enumerate(header, start=1):
        if not name:
            raise InvalidInputError(
                f"Kolumna nr {i} w nagłówku nie ma nazwy.",
                "Pierwszy wiersz pliku CSV musi zawierać nazwy wszystkich kolumn.",
            )
    duplicates = sorted({n for n in header if header.count(n) > 1})
    if duplicates:
        raise InvalidInputError(
            f"Powtórzone nazwy kolumn w nagłówku: {', '.join(duplicates)}.",
            "Nadaj kolumnom unikalne nazwy – w JSON każda staje się osobnym kluczem.",
        )
    return header


@converter("csv", "json")
def csv_to_json(source: Path, target: Path) -> None:
    text = _read_text(source)
    if not text.strip():
        raise InvalidInputError("Plik CSV jest pusty.", "Wybierz plik z nagłówkiem i danymi.")

    first_line = text.lstrip("\r\n").split("\n", 1)[0]
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=detect_delimiter(first_line))

    records: list[dict[str, str]] = []
    try:
        header = _validate_header(next(row for row in reader if row))  # pomija puste linie na początku
        for row in reader:
            if not row:  # pusta linia
                continue
            if len(row) != len(header):
                raise InvalidInputError(
                    f"Wiersz {reader.line_num}: {len(row)} pól, a nagłówek ma {len(header)} kolumn.",
                    "Popraw liczbę separatorów w tym wierszu albo ujmij tekst z separatorem w cudzysłów.",
                )
            records.append(dict(zip(header, row)))
    except csv.Error as exc:
        raise InvalidInputError(
            f"Uszkodzony plik CSV (wiersz {reader.line_num}): {exc}.",
            "Sprawdź, czy wszystkie cudzysłowy są zamknięte.",
        ) from exc

    with target.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _to_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):  # bool sprawdzamy przed int (True jest też intem)
        return "true" if value else "false"
    return str(value)


@converter("json", "csv")
def json_to_csv(source: Path, target: Path) -> None:
    text = _read_text(source)
    if not text.strip():
        raise InvalidInputError("Plik JSON jest pusty.", "Wybierz plik zawierający tablicę obiektów.")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidInputError(
            f"Niepoprawny JSON: {exc.msg} (wiersz {exc.lineno}, kolumna {exc.colno}).",
            "Sprawdź przecinki, cudzysłowy i nawiasy w podanym miejscu.",
        ) from exc

    if isinstance(data, dict):
        raise InvalidInputError(
            "JSON zawiera pojedynczy obiekt, a oczekiwana jest tablica obiektów.",
            'Otocz obiekt nawiasami kwadratowymi: [ {...} ].',
        )
    if not isinstance(data, list):
        raise InvalidInputError(
            "Oczekiwana jest tablica obiektów [ {...}, {...} ].",
            "Każdy obiekt w tablicy to jeden wiersz CSV.",
        )
    if not data:
        raise InvalidInputError(
            "Tablica JSON jest pusta – nie ma z czego zbudować nagłówka CSV.",
            "Dodaj co najmniej jeden obiekt.",
        )

    columns: list[str] = []
    for i, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise InvalidInputError(
                f"Element nr {i} tablicy nie jest obiektem (jest: {type(item).__name__}).",
                'Każdy element musi mieć postać {"kolumna": wartość}.',
            )
        for key, value in item.items():
            if isinstance(value, (dict, list)):
                raise InvalidInputError(
                    f"Element nr {i}, pole „{key}”: zagnieżdżone obiekty i listy nie są obsługiwane.",
                    "Spłaszcz dane – każda wartość musi być tekstem, liczbą, true/false albo null.",
                )
            if key not in columns:
                columns.append(key)

    with target.open("w", encoding=OUTPUT_CSV_ENCODING, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, restval="", delimiter=OUTPUT_CSV_DELIMITER)
        writer.writeheader()
        for item in data:
            writer.writerow({k: _to_cell(v) for k, v in item.items()})
