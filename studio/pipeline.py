"""Lab 6: skrypt czyszczący zbiór California Housing i tworzący raport przed/po.

Uruchomienie (w folderze projektu):
    python -m studio.pipeline
    python -m studio.pipeline dane_testowe/california_housing_z_problemami.csv --wyniki wyniki

Wynik (w katalogu --wyniki):
    cleaned.csv          dane po czyszczeniu
    raport_zmian.csv     dziennik operacji (ile rekordów zmieniła każda)
    profil_przed.csv / profil_po.csv     profil kolumn
    jakosc_przed.csv / jakosc_po.csv     raport reguł jakości
    raport.txt           całość w formie czytelnej dla człowieka

Wszystkie kroki są deterministyczne – ponowne uruchomienie daje identyczne pliki
(poza godziną w kolumnie „czas” dziennika).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import profile
from .errors import StudioError
from .rules import RangeRule
from .session import DataSession

DEFAULT_INPUT = Path("dane_testowe/california_housing_z_problemami.csv")

# Reguły zakresu – uzasadnienie w README:
#  - HouseAge: wiek budynku nie może być ujemny (w danych są wartości -5),
#  - AveRooms: średnio > 200 pokoi na mieszkanie jest fizycznie nierealne
#    (w oryginalnym zbiorze maksimum to ok. 142; w danych są sztuczne wartości 1000).
RANGE_RULES = [
    RangeRule("HouseAge", minimum=0, maximum=100),
    RangeRule("AveRooms", minimum=0, maximum=200),
]
# Uzupełnianie braków medianą (odporna na wartości skrajne).
MEDIAN_FILL = ["MedInc", "HouseAge", "AveRooms"]
# Braki w kolumnie tekstowej: usunięcie wierszy (druga strategia braków).
DROP_MISSING = ["Region"]
# Wartości odstające IQR – tylko OZNACZAMY (mogą być prawdziwe, np. duże osiedla).
FLAG_OUTLIERS = ["AveOccup", "Population"]


def clean_california(session: DataSession) -> None:
    """Domyślny pipeline czyszczenia. Kroki dla nieistniejących kolumn są pomijane."""
    columns = set(session.current.columns)
    session.drop_duplicates()
    for rule in RANGE_RULES:
        if rule.column in columns:
            session.apply_range_rule(rule, action="set_missing")
    for column in MEDIAN_FILL:
        if column in columns:
            session.fill_missing(column, strategy="median")
    present = [c for c in DROP_MISSING if c in columns]
    if present:
        session.drop_missing(present)
    for column in FLAG_OUTLIERS:
        if column in columns:
            session.handle_outliers(column, action="flag", factor=1.5)


def build_text_report(session: DataSession, quality_before, quality_after) -> str:
    log = session.log_frame().drop(columns=["czas"])
    return "\n\n".join([
        f"RAPORT JAKOŚCI DANYCH – {session.source}",
        profile.summary_text(session.raw, "PRZED czyszczeniem"),
        "=== Reguły jakości PRZED ===\n" + quality_before.to_string(index=False),
        "=== Dziennik zmian ===\n" + log.to_string(index=False),
        profile.summary_text(session.current, "PO czyszczeniu"),
        "=== Reguły jakości PO ===\n" + quality_after.to_string(index=False),
    ]) + "\n"


def run(input_path: Path, output_dir: Path) -> DataSession:
    session = DataSession.from_csv(input_path)
    iqr_columns = profile.numeric_columns(session.raw)
    rules = [r for r in RANGE_RULES if r.column in session.raw.columns]

    quality_before = session.quality_report(rules, iqr_columns, raw=True)
    clean_california(session)
    quality_after = session.quality_report(rules, iqr_columns)

    output_dir.mkdir(parents=True, exist_ok=True)
    session.export_cleaned(output_dir / "cleaned.csv")
    session.export_log(output_dir / "raport_zmian.csv")
    profile.column_profile(session.raw).to_csv(output_dir / "profil_przed.csv", encoding="utf-8-sig")
    profile.column_profile(session.current).to_csv(output_dir / "profil_po.csv", encoding="utf-8-sig")
    quality_before.to_csv(output_dir / "jakosc_przed.csv", index=False, encoding="utf-8-sig")
    quality_after.to_csv(output_dir / "jakosc_po.csv", index=False, encoding="utf-8-sig")
    text = build_text_report(session, quality_before, quality_after)
    (output_dir / "raport.txt").write_text(text, encoding="utf-8")
    return session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="studio.pipeline", description="Czyszczenie danych i raport przed/po")
    parser.add_argument("plik", nargs="?", type=Path, default=DEFAULT_INPUT, help="plik CSV")
    parser.add_argument("--wyniki", type=Path, default=Path("wyniki"), help="katalog na wyniki")
    args = parser.parse_args(argv)
    try:
        session = run(args.plik, args.wyniki)
    except StudioError as exc:
        print(f"BŁĄD: {exc}", file=sys.stderr)
        return 1

    before, after = profile.summary(session.raw), profile.summary(session.current)
    print(f"Wczytano: {session.source} ({before['wiersze']} wierszy, separator {session.separator!r})")
    print(session.log_frame().drop(columns=["czas"]).to_string(index=False))
    print(f"\nPrzed: {before['wiersze']} wierszy, braki {before['braki']}, duplikaty {before['pelne_duplikaty']}")
    print(f"Po:    {after['wiersze']} wierszy, braki {after['braki']}, duplikaty {after['pelne_duplikaty']}")
    print(f"\nZapisano wyniki w katalogu: {args.wyniki}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
