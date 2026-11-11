"""Wczytywanie plików CSV z kontrolą błędów.

Zasady:
- kodowanie UTF-8 (z BOM lub bez); inne kodowanie -> kontrolowany błąd z instrukcją,
- separator wykrywany z pierwszej linii: przecinek, średnik albo tabulator,
- wiersz z inną liczbą pól niż nagłówek -> błąd z numerem wiersza (nie pomijamy go po cichu,
  bo użytkownik straciłby dane bez informacji),
- plik pusty albo bez rekordów -> błąd.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd

from .errors import DataLoadError

ENCODING = "utf-8-sig"
CANDIDATE_SEPARATORS = [",", ";", "\t"]


def detect_separator(first_line: str) -> str:
    """Najczęstszy z kandydatów w nagłówku; brak separatora -> przecinek (jedna kolumna)."""
    counts = {sep: first_line.count(sep) for sep in CANDIDATE_SEPARATORS}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def read_first_line(path: Path) -> str:
    try:
        with path.open(encoding=ENCODING) as f:
            return f.readline()
    except UnicodeDecodeError as exc:
        raise _encoding_error(path, exc) from exc


def _encoding_error(path: Path, exc: UnicodeDecodeError) -> DataLoadError:
    return DataLoadError(
        f"Plik {path.name} nie jest zapisany w UTF-8 (błędny bajt na pozycji {exc.start}).",
        "Zapisz plik ponownie jako CSV UTF-8 (Excel: Zapisz jako -> CSV UTF-8).",
    )


def load_csv(path: str | Path) -> tuple[pd.DataFrame, str]:
    """Wczytuje CSV. Zwraca (DataFrame, użyty separator)."""
    path = Path(path)
    if not path.is_file():
        raise DataLoadError(f"Nie znaleziono pliku: {path}", "Sprawdź ścieżkę i wybierz plik ponownie.")

    first_line = read_first_line(path)
    if not first_line.strip():
        raise DataLoadError(f"Plik {path.name} jest pusty.", "Wybierz plik z nagłówkiem i danymi.")
    sep = detect_separator(first_line)

    try:
        frame = pd.read_csv(path, sep=sep, encoding=ENCODING, on_bad_lines="error")
    except UnicodeDecodeError as exc:
        raise _encoding_error(path, exc) from exc
    except pd.errors.ParserError as exc:
        raise DataLoadError(_describe_parser_error(path, exc), "Popraw liczbę separatorów w tym wierszu.") from exc
    except pd.errors.EmptyDataError as exc:
        raise DataLoadError(f"Plik {path.name} nie zawiera danych.", "Wybierz plik z nagłówkiem i danymi.") from exc

    if frame.empty:
        raise DataLoadError(f"Plik {path.name} nie zawiera rekordów (jest tylko nagłówek).", "Wybierz plik z danymi.")
    header = next(csv.reader([first_line.rstrip("\r\n")], delimiter=sep))
    duplicated_cols = sorted({name.strip() for name in header if header.count(name) > 1})
    if duplicated_cols:
        raise DataLoadError(
            f"Powtórzone nazwy kolumn w nagłówku: {', '.join(duplicated_cols)}.",
            "Nadaj kolumnom unikalne nazwy.",
        )
    return frame, sep


def _describe_parser_error(path: Path, exc: Exception) -> str:
    """pandas: 'Expected 3 fields in line 3, saw 4' -> czytelny komunikat po polsku."""
    match = re.search(r"Expected (\d+) fields in line (\d+), saw (\d+)", str(exc))
    if match:
        expected, line, saw = match.groups()
        return f"Wadliwy wiersz {line} w pliku {path.name}: {saw} pól, a nagłówek ma {expected} kolumny."
    return f"Nie udało się odczytać pliku {path.name}: {exc}"
