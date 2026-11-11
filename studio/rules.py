"""Reguły jakości: zakres poprawnych wartości i wykrywanie wartości odstających (IQR).

Reguły tylko WYKRYWAJĄ problemy (zwracają maskę / raport). O tym, co zrobić z wykrytymi
rekordami, decyduje osobna operacja czyszczenia wybrana przez użytkownika.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from .errors import ColumnError, ParameterError


def require_column(df: pd.DataFrame, column: str) -> None:
    if column not in df.columns:
        raise ColumnError(f"Brak kolumny „{column}” w danych.", f"Dostępne kolumny: {', '.join(map(str, df.columns))}.")


def require_numeric(df: pd.DataFrame, column: str) -> pd.Series:
    require_column(df, column)
    if not pd.api.types.is_numeric_dtype(df[column]) or pd.api.types.is_bool_dtype(df[column]):
        raise ColumnError(
            f"Kolumna „{column}” nie jest liczbowa (typ: {df[column].dtype}).",
            "Wybierz kolumnę z wartościami liczbowymi.",
        )
    return df[column]


@dataclass(frozen=True)
class RangeRule:
    """Wartości kolumny powinny mieścić się w [minimum, maximum]. None = brak ograniczenia."""

    column: str
    minimum: float | None = None
    maximum: float | None = None

    def validate(self, df: pd.DataFrame) -> None:
        require_numeric(df, self.column)
        if self.minimum is None and self.maximum is None:
            raise ParameterError("Reguła zakresu nie ma ani minimum, ani maksimum.", "Podaj co najmniej jedną granicę.")
        for name, value in (("minimum", self.minimum), ("maksimum", self.maximum)):
            if value is not None and (not isinstance(value, (int, float)) or math.isnan(value)):
                raise ParameterError(f"Niepoprawne {name}: {value!r}.", "Podaj liczbę.")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ParameterError(
                f"Minimum ({self.minimum}) jest większe od maksimum ({self.maximum}).", "Zamień granice miejscami."
            )

    def violations(self, df: pd.DataFrame) -> pd.Series:
        """Maska wierszy z wartością poza zakresem. Braki NIE są naruszeniem (to osobny problem)."""
        self.validate(df)
        values = df[self.column]
        mask = pd.Series(False, index=df.index)
        if self.minimum is not None:
            mask |= values < self.minimum
        if self.maximum is not None:
            mask |= values > self.maximum
        return mask & values.notna()

    def describe(self) -> str:
        low = "-∞" if self.minimum is None else f"{self.minimum:g}"
        high = "+∞" if self.maximum is None else f"{self.maximum:g}"
        return f"{self.column} ∈ [{low}, {high}]"


def iqr_bounds(df: pd.DataFrame, column: str, factor: float = 1.5) -> tuple[float, float] | None:
    """Granice Q1 − k·IQR i Q3 + k·IQR. None, gdy IQR = 0 lub brak danych (metoda nic nie wykryje)."""
    if factor <= 0:
        raise ParameterError(f"Współczynnik IQR musi być dodatni (podano {factor}).", "Typowa wartość to 1.5 lub 3.")
    values = require_numeric(df, column).dropna()
    if values.empty:
        return None
    q1, q3 = values.quantile([0.25, 0.75])
    iqr = q3 - q1
    if iqr == 0:
        return None
    return float(q1 - factor * iqr), float(q3 + factor * iqr)


def iqr_mask(df: pd.DataFrame, column: str, factor: float = 1.5) -> pd.Series:
    """Maska wartości odstających wg reguły IQR (braki nie są odstające)."""
    bounds = iqr_bounds(df, column, factor)
    if bounds is None:
        return pd.Series(False, index=df.index)
    low, high = bounds
    values = df[column]
    return ((values < low) | (values > high)) & values.notna()


def quality_report(
    df: pd.DataFrame,
    range_rules: list[RangeRule] = (),
    iqr_columns: list[str] = (),
    factor: float = 1.5,
) -> pd.DataFrame:
    """Raport reguł jakości: ile rekordów narusza każdą regułę. Danych nie zmienia."""
    rows = []
    total = len(df)
    for rule in range_rules:
        count = int(rule.violations(df).sum())
        rows.append({"regula": "zakres", "kolumna": rule.column, "parametry": rule.describe(),
                     "naruszenia": count, "procent": round(count / total * 100, 2) if total else 0.0})
    for column in iqr_columns:
        bounds = iqr_bounds(df, column, factor)
        params = "IQR = 0 – brak wykrywania" if bounds is None else f"k={factor}, [{bounds[0]:.4g}, {bounds[1]:.4g}]"
        count = int(iqr_mask(df, column, factor).sum())
        rows.append({"regula": "IQR", "kolumna": column, "parametry": params,
                     "naruszenia": count, "procent": round(count / total * 100, 2) if total else 0.0})
    return pd.DataFrame(rows, columns=["regula", "kolumna", "parametry", "naruszenia", "procent"])
