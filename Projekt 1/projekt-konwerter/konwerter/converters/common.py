"""Funkcje pomocnicze wspólne dla wielu konwerterów."""

from __future__ import annotations

from pathlib import Path

from ..errors import InvalidInputError

INPUT_ENCODING = "utf-8-sig"   # czyta UTF-8 z BOM i bez BOM


def read_text_utf8(path: Path) -> str:
    """Wczytuje plik tekstowy jako UTF-8.

    newline='' zostawia znaki końca linii bez zmian (ważne dla pól wieloliniowych w CSV).
    """
    try:
        with path.open(encoding=INPUT_ENCODING, newline="") as f:
            return f.read()
    except UnicodeDecodeError as exc:
        raise InvalidInputError(
            f"Plik {path.name} nie jest zapisany w UTF-8 (błędny bajt na pozycji {exc.start}).",
            "Zapisz plik ponownie z kodowaniem UTF-8 (np. Notatnik: Zapisz jako -> Kodowanie UTF-8).",
        ) from exc
