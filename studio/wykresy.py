"""Lab 7: zestaw wykresów dla danych przed i po czyszczeniu.

Uruchomienie (w folderze projektu):
    python -m studio.wykresy
    python -m studio.wykresy dane_testowe/california_housing_z_problemami.csv --wyniki wyniki

Zapisuje do <wyniki>/wykresy/ pliki PNG (i korelację także w PDF i SVG) oraz wnioski.txt.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import charts
from .errors import StudioError
from .pipeline import DEFAULT_INPUT, clean_california
from .session import DataSession


def make_charts(session: DataSession, folder: Path) -> list[Path]:
    raw, clean = session.raw, session.current
    figures = {
        # przed/po – widać efekt czyszczenia (AveRooms 1000 -> mediana, HouseAge -5 -> mediana)
        "01_aveRooms_przed_po.png": charts.before_after_figure(raw, clean, "AveRooms", "histogram"),
        "02_houseAge_przed_po.png": charts.before_after_figure(raw, clean, "HouseAge", "pudelkowy"),
        # 4 wymagane typy na danych po czyszczeniu
        "03_histogram_medHouseVal.png": charts.histogram_figure(clean, "MedHouseVal"),
        "04_punktowy_medInc_medHouseVal.png": charts.scatter_figure(clean, "MedInc", "MedHouseVal", hue="Region"),
        "05_pudelkowy_medHouseVal_region.png": charts.box_figure(clean, "MedHouseVal", by="Region"),
        "06_slupkowy_region_przed.png": charts.bar_figure(raw, "Region"),
        "07_slupkowy_medHouseVal_region.png": charts.bar_figure(clean, "Region", value="MedHouseVal", agg="median"),
        "08_korelacja.png": charts.correlation_figure(clean),
    }
    saved = [charts.save_figure(fig, folder / name) for name, fig in figures.items()]
    saved.append(charts.save_figure(figures["08_korelacja.png"], folder / "08_korelacja.pdf"))
    saved.append(charts.save_figure(figures["08_korelacja.png"], folder / "08_korelacja.svg"))
    (folder / "wnioski.txt").write_text(charts.correlation_conclusions(clean) + "\n", encoding="utf-8")
    return saved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="studio.wykresy", description="Wykresy przed/po czyszczeniu")
    parser.add_argument("plik", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--wyniki", type=Path, default=Path("wyniki"))
    args = parser.parse_args(argv)
    try:
        session = DataSession.from_csv(args.plik)
        clean_california(session)
        saved = make_charts(session, args.wyniki / "wykresy")
    except StudioError as exc:
        print(f"BŁĄD: {exc}", file=sys.stderr)
        return 1
    for path in saved:
        print(f"Zapisano: {path}")
    print()
    print(charts.correlation_conclusions(session.current))
    return 0


if __name__ == "__main__":
    sys.exit(main())
