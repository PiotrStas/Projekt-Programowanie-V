"""Profil danych: rozmiar, typy, statystyki opisowe, braki, duplikaty i unikalność.

Funkcje tylko CZYTAJĄ DataFrame – niczego nie zmieniają.
"""

from __future__ import annotations

import pandas as pd


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]


def categorical_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in numeric_columns(df)]


def summary(df: pd.DataFrame) -> dict[str, int | float]:
    """Najważniejsze liczby o całym zbiorze."""
    cells = df.size
    missing = int(df.isna().sum().sum())
    return {
        "wiersze": len(df),
        "kolumny": df.shape[1],
        "kolumny_liczbowe": len(numeric_columns(df)),
        "kolumny_tekstowe": len(categorical_columns(df)),
        "braki": missing,
        "braki_pct": round(missing / cells * 100, 2) if cells else 0.0,
        "wiersze_z_brakami": int(df.isna().any(axis=1).sum()),
        "pelne_duplikaty": int(df.duplicated().sum()),
    }


def column_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Jedna linia na kolumnę: typ, braki, unikalność i statystyki (dla liczb)."""
    profile = pd.DataFrame({
        "typ": df.dtypes.astype(str),
        "braki": df.isna().sum(),
        "braki_pct": df.isna().mean().mul(100).round(2),
        "unikalne": df.nunique(dropna=True),
    })
    numeric = numeric_columns(df)
    if numeric:
        stats = df[numeric].describe().T.rename(columns={
            "mean": "srednia", "std": "odch_std", "min": "min", "25%": "q1",
            "50%": "mediana", "75%": "q3", "max": "max",
        })
        profile = profile.join(stats[["min", "q1", "mediana", "srednia", "q3", "max", "odch_std"]].round(4))
    categorical = categorical_columns(df)
    if categorical:
        top = {c: (df[c].mode(dropna=True).iloc[0] if df[c].notna().any() else None) for c in categorical}
        profile["najczestsza"] = pd.Series(top, dtype=object)
    profile.index.name = "kolumna"
    return profile


def is_constant(series: pd.Series) -> bool:
    """Kolumna bez zmienności (0 lub 1 unikalna wartość) – nie nadaje się do wykresu rozkładu."""
    return series.nunique(dropna=True) <= 1


def summary_text(df: pd.DataFrame, title: str = "Profil danych") -> str:
    """Czytelny opis do konsoli / pliku tekstowego."""
    s = summary(df)
    lines = [
        f"=== {title} ===",
        f"Rozmiar: {s['wiersze']} wierszy × {s['kolumny']} kolumn "
        f"({s['kolumny_liczbowe']} liczbowych, {s['kolumny_tekstowe']} tekstowych)",
        f"Braki: {s['braki']} komórek ({s['braki_pct']}%), wierszy z brakami: {s['wiersze_z_brakami']}",
        f"Pełne duplikaty: {s['pelne_duplikaty']}",
        "",
        column_profile(df).to_string(),
    ]
    return "\n".join(lines)
