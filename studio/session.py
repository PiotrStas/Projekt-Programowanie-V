"""Sesja pracy z danymi: dane surowe, dane bieżące i dziennik operacji (ślad zmian).

- `raw` nigdy się nie zmienia – reset przywraca z niego `current` bez ponownego wczytywania pliku,
- każda operacja czyszczenia działa na kopii `current` i dopisuje wpis do `log`,
- sesja nie wie nic o GUI – okno (Lab 8) będzie tylko wywoływać jej metody.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import cleaning
from .errors import ExportError
from .loader import load_csv
from .rules import RangeRule, quality_report


@dataclass(frozen=True)
class Operation:
    """Jeden wpis dziennika zmian."""

    nazwa: str
    parametry: str
    czas: str
    wiersze_przed: int
    wiersze_po: int
    zmienione_rekordy: int


@dataclass
class DataSession:
    raw: pd.DataFrame
    source: str = ""
    separator: str = ","
    current: pd.DataFrame = field(init=False)
    log: list[Operation] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.raw = self.raw.copy(deep=True)
        self.current = self.raw.copy(deep=True)

    @classmethod
    def from_csv(cls, path: str | Path) -> DataSession:
        frame, sep = load_csv(path)
        session = cls(frame, source=Path(path).name, separator=sep)
        session._record("wczytanie", f"plik={Path(path).name}, separator={sep!r}", 0, len(frame), 0)
        return session

    # ------------------------------------------------------------------ dziennik

    def _record(self, name: str, params: str, before: int, after: int, changed: int) -> Operation:
        op = Operation(name, params, datetime.now().isoformat(timespec="seconds"), before, after, changed)
        self.log.append(op)
        return op

    def _apply(self, name: str, params: str, func: Callable[[pd.DataFrame], tuple[pd.DataFrame, int]]) -> Operation:
        """Wykonuje operację na kopii danych; dopiero po sukcesie podmienia `current` i zapisuje wpis."""
        before = len(self.current)
        new_frame, changed = func(self.current)
        self.current = new_frame
        return self._record(name, params, before, len(new_frame), changed)

    def log_frame(self) -> pd.DataFrame:
        return pd.DataFrame([asdict(op) for op in self.log],
                            columns=["nazwa", "parametry", "czas", "wiersze_przed", "wiersze_po", "zmienione_rekordy"])

    # ------------------------------------------------------------------ operacje

    def drop_duplicates(self, subset: list[str] | None = None) -> Operation:
        params = "pełne duplikaty" if not subset else f"klucz={subset}"
        return self._apply("usuniecie_duplikatow", params, lambda df: cleaning.drop_duplicates(df, subset))

    def drop_missing(self, columns: list[str] | None = None) -> Operation:
        params = f"kolumny={columns}" if columns else "dowolna kolumna"
        return self._apply("usuniecie_brakow", params, lambda df: cleaning.drop_missing(df, columns))

    def fill_missing(self, column: str, strategy: str = "median", value: object = None) -> Operation:
        params = f"kolumna={column}, strategia={strategy}" + (f", wartosc={value!r}" if strategy == "constant" else "")
        return self._apply("uzupelnienie_brakow", params, lambda df: cleaning.fill_missing(df, column, strategy, value))

    def apply_range_rule(self, rule: RangeRule, action: str = "set_missing") -> Operation:
        params = f"{rule.describe()}, akcja={action}"
        return self._apply("regula_zakresu", params, lambda df: cleaning.apply_range_rule(df, rule, action))

    def handle_outliers(self, column: str, action: str = "flag", factor: float = 1.5) -> Operation:
        params = f"kolumna={column}, IQR k={factor}, akcja={action}"
        return self._apply("wartosci_odstajace", params, lambda df: cleaning.handle_outliers(df, column, action, factor))

    def reset(self) -> Operation:
        """Powrót do danych surowych bez ponownego wczytywania pliku. Dziennik zostaje (ślad, że był reset)."""
        before = len(self.current)
        self.current = self.raw.copy(deep=True)
        return self._record("reset", "przywrócono dane surowe", before, len(self.current), 0)

    # ------------------------------------------------------------------ raporty i eksport

    def quality_report(self, range_rules: list[RangeRule] = (), iqr_columns: list[str] = (),
                       factor: float = 1.5, raw: bool = False) -> pd.DataFrame:
        return quality_report(self.raw if raw else self.current, range_rules, iqr_columns, factor)

    def export_cleaned(self, path: str | Path) -> Path:
        return _write_csv(self.current, Path(path))

    def export_log(self, path: str | Path) -> Path:
        return _write_csv(self.log_frame(), Path(path))


def _write_csv(frame: pd.DataFrame, path: Path) -> Path:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False, encoding="utf-8-sig")
    except OSError as exc:
        raise ExportError(
            f"Nie udało się zapisać pliku {path.name}: {exc.strerror or exc}",
            "Sprawdź, czy plik nie jest otwarty w Excelu i czy masz prawo zapisu w katalogu.",
        ) from exc
    return path
