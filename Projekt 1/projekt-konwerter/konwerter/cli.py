"""Uruchamianie z wiersza poleceń. Bez argumentów otwiera okno (GUI).

Przykłady:
    python -m konwerter                       # okno programu
    python -m konwerter --lista
    python -m konwerter dane_testowe/studenci.csv --na json --do wyniki
    python -m konwerter dane_testowe/produkty.json --na csv --do wyniki --nadpisz
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .core import ConversionRequest, available_targets, execute, supported_pairs
from .errors import ConversionError

LOG_FILE = "konwerter.log"


def setup_logging() -> None:
    logging.basicConfig(
        filename=LOG_FILE,
        encoding="utf-8",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="konwerter", description="Uniwersalny konwerter plików")
    p.add_argument("plik", nargs="?", type=Path, help="plik wejściowy")
    p.add_argument("--na", dest="format", help="format docelowy, np. json")
    p.add_argument("--do", dest="katalog", type=Path, default=Path("."), help="katalog zapisu (domyślnie bieżący)")
    p.add_argument("--nadpisz", action="store_true", help="nadpisz istniejący plik zamiast tworzyć nową nazwę")
    p.add_argument("--lista", action="store_true", help="pokaż wspierane pary formatów")
    return p


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = build_parser().parse_args(argv)

    if args.lista:
        print("Wspierane konwersje:")
        for src, dst in supported_pairs():
            print(f"  {src} -> {dst}")
        return 0

    if args.plik is None:
        # bez argumentów: otwieramy okno (import dopiero tutaj – CLI działa nawet bez Tkintera)
        from .gui import run

        run()
        return 0

    if not args.format:
        targets = available_targets(args.plik)
        print(f"Dostępne formaty dla {args.plik.name}: {', '.join(targets) or 'brak'}")
        print("Podaj format opcją --na.")
        return 2

    try:  # wygoda w CLI: brakujący katalog wynikowy tworzymy sami
        args.katalog.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"BŁĄD: Nie można utworzyć katalogu {args.katalog}: {exc.strerror}", file=sys.stderr)
        return 1

    request = ConversionRequest(args.plik, args.format, args.katalog, overwrite=args.nadpisz)
    try:
        result = execute(request)
    except ConversionError as exc:
        print(f"BŁĄD: {exc}", file=sys.stderr)
        return 1
    print(f"OK: zapisano {result}")
    return 0
