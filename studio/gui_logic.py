from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from .charts import MAX_CATEGORIES
from .errors import ParameterError
from .profile import numeric_columns, summary
from .rules import RangeRule
from .session import DataSession, Operation

ALL_COLUMNS = "(wszystkie kolumny)"
ANY_COLUMN = "(dowolna kolumna)"

FILL_STRATEGIES = {
    "mediana": "median",
    "średnia": "mean",
    "dominanta (najczęstsza wartość)": "mode",
    "stała wartość": "constant",
}
RANGE_ACTIONS = {"zamień na brak": "set_missing", "przytnij do granic": "clip", "usuń wiersze": "drop"}
OUTLIER_ACTIONS = {"tylko oznacz (nowa kolumna)": "flag", "przytnij do granic IQR": "clip", "usuń wiersze": "drop"}


@dataclass(frozen=True)
class OperationSpec:
    label: str
    options: dict[str, str]
    params: tuple[str, ...]


OPERATIONS: dict[str, OperationSpec] = {
    "duplicates": OperationSpec("Usuń duplikaty", {}, ()),
    "fill": OperationSpec("Uzupełnij braki", FILL_STRATEGIES, ("value",)),
    "drop_missing": OperationSpec("Usuń wiersze z brakami", {}, ()),
    "range": OperationSpec("Reguła zakresu (wartości błędne)", RANGE_ACTIONS, ("min", "max")),
    "outliers": OperationSpec("Wartości odstające (IQR)", OUTLIER_ACTIONS, ("factor",)),
}
OPERATION_BY_LABEL = {spec.label: key for key, spec in OPERATIONS.items()}


def valid_columns(df: pd.DataFrame | None, operation: str, option: str = "") -> list[str]:
    if df is None:
        return []
    numeric = [str(c) for c in numeric_columns(df)]
    every = [str(c) for c in df.columns if not pd.api.types.is_bool_dtype(df[c])]
    if operation == "duplicates":
        return [ALL_COLUMNS] + every
    if operation == "drop_missing":
        return [ANY_COLUMN] + every
    if operation == "fill":
        strategy = FILL_STRATEGIES.get(option, option)
        return numeric if strategy in ("median", "mean") else every
    if operation in ("range", "outliers"):
        return numeric
    raise ParameterError(f"Nieznana operacja: {operation}.", "Wybierz operację z listy.")


def parse_number(text: str, name: str, required: bool = True) -> float | None:
    text = (text or "").strip().replace(",", ".")
    if not text:
        if required:
            raise ParameterError(f"Nie podano wartości: {name}.", "Wpisz liczbę.")
        return None
    try:
        value = float(text)
    except ValueError as exc:
        raise ParameterError(f"„{text}” nie jest liczbą ({name}).", "Wpisz liczbę, np. 0 albo 1.5.") from exc
    if math.isnan(value) or math.isinf(value):
        raise ParameterError(f"Niepoprawna wartość: {name} = {text}.", "Wpisz zwykłą liczbę.")
    return value


def run_operation(session: DataSession, operation: str, column: str, option: str,
                  params: dict[str, str]) -> Operation:
    if operation not in OPERATIONS:
        raise ParameterError(f"Nieznana operacja: {operation}.", "Wybierz operację z listy.")
    spec = OPERATIONS[operation]
    if spec.options and option not in spec.options:
        raise ParameterError("Nie wybrano wariantu operacji.", "Wybierz strategię / akcję z listy.")
    needs_column = operation in ("fill", "range", "outliers")
    if needs_column and not column:
        raise ParameterError("Nie wybrano kolumny.", "Wybierz kolumnę z listy.")

    if operation == "duplicates":
        return session.drop_duplicates(None if column in ("", ALL_COLUMNS) else [column])
    if operation == "drop_missing":
        return session.drop_missing(None if column in ("", ANY_COLUMN) else [column])
    if operation == "fill":
        strategy = spec.options[option]
        value = params.get("value", "") if strategy == "constant" else None
        return session.fill_missing(column, strategy, value)
    if operation == "range":
        low = parse_number(params.get("min", ""), "minimum", required=False)
        high = parse_number(params.get("max", ""), "maksimum", required=False)
        return session.apply_range_rule(RangeRule(column, low, high), spec.options[option])
    factor = parse_number(params.get("factor", "") or "1.5", "współczynnik IQR")
    return session.handle_outliers(column, spec.options[option], factor)


def preview_rows(df: pd.DataFrame, limit: int = 200) -> list[tuple[str, ...]]:
    head = df.head(limit)
    rows = []
    for record in head.itertuples(index=False):
        rows.append(tuple("" if pd.isna(v) else (f"{v:.6g}" if isinstance(v, float) else str(v)) for v in record))
    return rows


def summary_lines(session: DataSession) -> list[str]:
    raw, cur = summary(session.raw), summary(session.current)
    return [
        f"Plik: {session.source}   (separator {session.separator!r})",
        f"Wiersze: {cur['wiersze']}  (surowe: {raw['wiersze']})     Kolumny: {cur['kolumny']} "
        f"({cur['kolumny_liczbowe']} liczbowych, {cur['kolumny_tekstowe']} tekstowych)",
        f"Braki: {cur['braki']} komórek ({cur['braki_pct']}%), wierszy z brakami: {cur['wiersze_z_brakami']}"
        f"     Pełne duplikaty: {cur['pelne_duplikaty']}",
    ]


CHART_TYPES = {
    "Histogram": "histogram",
    "Wykres punktowy": "punktowy",
    "Wykres pudełkowy": "pudelkowy",
    "Wykres słupkowy": "slupkowy",
    "Macierz korelacji": "korelacja",
}
NONE = "(brak)"


@dataclass(frozen=True)
class ChartField:
    label: str
    kind: str
    required: bool


CHART_FIELDS: dict[str, tuple[ChartField, ...]] = {
    "histogram": (ChartField("Kolumna", "numeric", True),),
    "punktowy": (ChartField("Oś X", "numeric", True), ChartField("Oś Y", "numeric", True),
                 ChartField("Kolor wg", "category", False)),
    "pudelkowy": (ChartField("Kolumna", "numeric", True), ChartField("Grupuj wg", "category", False)),
    "slupkowy": (ChartField("Kategoria", "category", True), ChartField("Wartość (mediana)", "numeric", False)),
    "korelacja": (),
}
CHART_PARAM_NAMES = {
    "histogram": ("column",),
    "punktowy": ("x", "y", "hue"),
    "pudelkowy": ("column", "by"),
    "slupkowy": ("column", "value"),
    "korelacja": (),
}


def chart_numeric_columns(df: pd.DataFrame | None) -> list[str]:
    if df is None:
        return []
    return [str(c) for c in numeric_columns(df) if df[c].nunique(dropna=True) > 1]


def chart_category_columns(df: pd.DataFrame | None) -> list[str]:
    if df is None:
        return []
    numeric = set(numeric_columns(df))
    return [str(c) for c in df.columns
            if c not in numeric and not pd.api.types.is_bool_dtype(df[c])
            and 0 < df[c].nunique(dropna=True) <= MAX_CATEGORIES]


def chart_choices(df: pd.DataFrame | None, kind: str) -> list[list[str]]:
    lists = {"numeric": chart_numeric_columns(df), "category": chart_category_columns(df)}
    return [lists[f.kind] if f.required else [NONE] + lists[f.kind] for f in CHART_FIELDS[kind]]


def chart_params(kind: str, selected: list[str]) -> dict[str, str]:
    if kind not in CHART_FIELDS:
        raise ParameterError(f"Nieznany typ wykresu: {kind}.", "Wybierz typ wykresu z listy.")
    params = {}
    for field, name, value in zip(CHART_FIELDS[kind], CHART_PARAM_NAMES[kind], selected):
        if value in ("", NONE):
            if field.required:
                raise ParameterError(f"Nie wybrano: {field.label}.", "Wybierz kolumnę z listy.")
            continue
        params[name] = value
    if kind == "slupkowy" and "value" in params:
        params["agg"] = "median"
    return params
