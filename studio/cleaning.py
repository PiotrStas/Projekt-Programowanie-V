"""Operacje czyszczenia jako czyste funkcje.

Każda funkcja:
- dostaje DataFrame i NIE zmienia go (pracuje na kopii),
- zmienia wyłącznie wskazane kolumny,
- zwraca (nowy DataFrame, liczba rekordów dotkniętych operacją).

Zapis do dziennika zmian robi DataSession – tutaj jest tylko logika.
"""

from __future__ import annotations

import pandas as pd

from .errors import ColumnError, ParameterError
from .rules import RangeRule, iqr_bounds, iqr_mask, require_column, require_numeric

FILL_STRATEGIES = ("median", "mean", "mode", "constant")
RANGE_ACTIONS = ("set_missing", "clip", "drop")
OUTLIER_ACTIONS = ("flag", "clip", "drop")
FLAG_SUFFIX = "_odstajaca"


def drop_duplicates(df: pd.DataFrame, subset: list[str] | None = None) -> tuple[pd.DataFrame, int]:
    """Usuwa pełne duplikaty (subset=None) albo duplikaty według wskazanego klucza. Zostaje pierwsze wystąpienie."""
    if subset:
        for column in subset:
            require_column(df, column)
    result = df.drop_duplicates(subset=subset or None, keep="first").copy()
    return result, len(df) - len(result)


def drop_missing(df: pd.DataFrame, columns: list[str] | None = None) -> tuple[pd.DataFrame, int]:
    """Usuwa wiersze z brakiem we wskazanych kolumnach (None = w dowolnej kolumnie)."""
    for column in columns or []:
        require_column(df, column)
    result = df.dropna(subset=columns or None).copy()
    return result, len(df) - len(result)


def fill_missing(
    df: pd.DataFrame, column: str, strategy: str = "median", value: object = None
) -> tuple[pd.DataFrame, int]:
    """Uzupełnia braki w JEDNEJ kolumnie: mediana / średnia (liczby), dominanta, stała."""
    require_column(df, column)
    if strategy not in FILL_STRATEGIES:
        raise ParameterError(f"Nieznana strategia: {strategy}.", f"Dostępne: {', '.join(FILL_STRATEGIES)}.")
    missing = df[column].isna()
    count = int(missing.sum())
    result = df.copy()
    if count == 0:
        return result, 0

    if strategy in ("median", "mean"):
        series = require_numeric(df, column)
        if series.notna().sum() == 0:
            raise ColumnError(f"Kolumna „{column}” nie ma żadnych wartości – nie da się policzyć {strategy}.",
                              "Użyj stałej wartości albo usuń wiersze.")
        fill_value = series.median() if strategy == "median" else series.mean()
    elif strategy == "mode":
        modes = df[column].mode(dropna=True)
        if modes.empty:
            raise ColumnError(f"Kolumna „{column}” nie ma żadnych wartości – brak dominanty.",
                              "Użyj stałej wartości albo usuń wiersze.")
        fill_value = modes.iloc[0]
    else:
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ParameterError("Nie podano wartości do uzupełnienia.", "Wpisz wartość stałą.")
        fill_value = value
        if pd.api.types.is_numeric_dtype(df[column]):
            try:
                fill_value = float(value)
            except (TypeError, ValueError) as exc:
                raise ParameterError(f"Kolumna „{column}” jest liczbowa, a podano „{value}”.", "Podaj liczbę.") from exc

    result[column] = result[column].fillna(fill_value)
    return result, count


def apply_range_rule(df: pd.DataFrame, rule: RangeRule, action: str = "set_missing") -> tuple[pd.DataFrame, int]:
    """Obsługa wartości poza zakresem: zamiana na brak, przycięcie do granic albo usunięcie wierszy."""
    if action not in RANGE_ACTIONS:
        raise ParameterError(f"Nieznana akcja: {action}.", f"Dostępne: {', '.join(RANGE_ACTIONS)}.")
    mask = rule.violations(df)
    count = int(mask.sum())
    result = df.copy()
    if count == 0:
        return result, 0
    if action == "set_missing":
        result[rule.column] = result[rule.column].astype(float)
        result.loc[mask, rule.column] = float("nan")
    elif action == "clip":
        result[rule.column] = result[rule.column].clip(lower=rule.minimum, upper=rule.maximum)
    else:
        result = result.loc[~mask].copy()
    return result, count


def handle_outliers(
    df: pd.DataFrame, column: str, action: str = "flag", factor: float = 1.5
) -> tuple[pd.DataFrame, int]:
    """Wartości odstające wg IQR: oznaczenie (nowa kolumna logiczna), przycięcie albo usunięcie."""
    if action not in OUTLIER_ACTIONS:
        raise ParameterError(f"Nieznana akcja: {action}.", f"Dostępne: {', '.join(OUTLIER_ACTIONS)}.")
    mask = iqr_mask(df, column, factor)
    count = int(mask.sum())
    result = df.copy()
    if action == "flag":
        result[f"{column}{FLAG_SUFFIX}"] = mask
    elif count and action == "clip":
        low, high = iqr_bounds(df, column, factor)
        result[column] = result[column].clip(lower=low, upper=high)
    elif count:
        result = result.loc[~mask].copy()
    return result, count
