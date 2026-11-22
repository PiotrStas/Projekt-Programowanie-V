"""Wykresy (Lab 7): histogram, punktowy, pudełkowy, słupkowy i macierz korelacji.

Zasady:
- każda funkcja ZWRACA obiekt Figure – ten sam wykres można osadzić w oknie Tkinter
  (FigureCanvasTkAgg) albo zapisać do PNG/PDF/SVG,
- używamy matplotlib.figure.Figure, a NIE pyplot: pyplot trzyma „bieżący wykres” w zmiennej
  globalnej, a Figure jest zwykłym obiektem – bez ukrytego stanu i bezpieczny w GUI,
- przed rysowaniem sprawdzamy typ kolumny: zły typ albo kolumna stała -> ColumnError
  z komunikatem, zamiast pustego lub mylącego wykresu.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure

from .errors import ColumnError, ExportError, ParameterError
from .profile import is_constant
from .rules import require_column

# Czytelne opisy osi dla zbioru California Housing; inne kolumny – sama nazwa.
COLUMN_LABELS = {
    "MedInc": "Mediana dochodu [10 tys. USD]",
    "HouseAge": "Mediana wieku budynków [lata]",
    "AveRooms": "Średnia liczba pokoi na gospodarstwo",
    "AveBedrms": "Średnia liczba sypialni na gospodarstwo",
    "Population": "Liczba mieszkańców bloku",
    "AveOccup": "Średnia liczba osób na gospodarstwo",
    "Latitude": "Szerokość geograficzna [°]",
    "Longitude": "Długość geograficzna [°]",
    "MedHouseVal": "Mediana wartości domu [100 tys. USD]",
    "Region": "Region",
}
MAX_CATEGORIES = 30
FIGSIZE = (7, 4.5)
SAVE_FORMATS = (".png", ".pdf", ".svg")


def label(column: str) -> str:
    return COLUMN_LABELS.get(column, column)


# ---------------------------------------------------------------- walidacja kolumn

def numeric_values(df: pd.DataFrame, column: str) -> pd.Series:
    """Wartości kolumny liczbowej bez braków. Błąd dla tekstu, pustej i stałej kolumny."""
    require_column(df, column)
    series = df[column]
    if not pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
        raise ColumnError(
            f"Kolumna „{column}” nie jest liczbowa – ten wykres wymaga liczb.",
            "Wybierz kolumnę liczbową albo użyj wykresu słupkowego.",
        )
    values = series.dropna()
    if values.empty:
        raise ColumnError(f"Kolumna „{column}” nie zawiera żadnych wartości.", "Wybierz inną kolumnę.")
    if is_constant(values):
        raise ColumnError(
            f"Kolumna „{column}” jest stała (jedna wartość: {values.iloc[0]}) – rozkład nic nie pokaże.",
            "Wybierz kolumnę, której wartości się różnią.",
        )
    return values


def categorical_values(df: pd.DataFrame, column: str) -> pd.Series:
    """Kolumna kategoryczna: tekst albo liczba o niewielu wartościach (≤ MAX_CATEGORIES)."""
    require_column(df, column)
    series = df[column]
    unique = series.nunique(dropna=True)
    if unique == 0:
        raise ColumnError(f"Kolumna „{column}” nie zawiera żadnych wartości.", "Wybierz inną kolumnę.")
    if unique > MAX_CATEGORIES:
        raise ColumnError(
            f"Kolumna „{column}” ma {unique} różnych wartości – za dużo na wykres słupkowy (max {MAX_CATEGORIES}).",
            "Wybierz kolumnę kategoryczną, np. Region, albo użyj histogramu.",
        )
    return series


def _new_figure() -> tuple[Figure, object]:
    fig = Figure(figsize=FIGSIZE, dpi=100)
    return fig, fig.add_subplot()


# ---------------------------------------------------------------- 4 typy wykresów

def histogram_figure(df: pd.DataFrame, column: str, bins: int = 50, title: str | None = None) -> Figure:
    """Rozkład jednej zmiennej liczbowej."""
    values = numeric_values(df, column)
    fig, ax = _new_figure()
    ax.hist(values, bins=bins, color="#4C72B0", edgecolor="white", linewidth=0.3)
    ax.set(title=title or f"Rozkład: {label(column)}", xlabel=label(column), ylabel="Liczba rekordów")
    fig.tight_layout()
    return fig


def scatter_figure(df: pd.DataFrame, x: str, y: str, hue: str | None = None, title: str | None = None) -> Figure:
    """Zależność między dwiema zmiennymi liczbowymi; opcjonalnie kolor wg kategorii."""
    if x == y:
        raise ParameterError("Oś X i oś Y to ta sama kolumna.", "Wybierz dwie różne kolumny.")
    numeric_values(df, x)
    numeric_values(df, y)
    columns = [x, y] + ([hue] if hue else [])
    if hue:
        categorical_values(df, hue)
    data = df[columns].dropna()
    fig, ax = _new_figure()
    # przy ~20 tys. punktów małe, półprzezroczyste kropki pokazują zagęszczenie
    sns.scatterplot(data=data, x=x, y=y, hue=hue, s=8, alpha=0.35, linewidth=0, ax=ax)
    r = data[x].corr(data[y])
    ax.set(title=title or f"{y} względem {x} (korelacja r = {r:.2f})", xlabel=label(x), ylabel=label(y))
    fig.tight_layout()
    return fig


def box_figure(df: pd.DataFrame, column: str, by: str | None = None, title: str | None = None) -> Figure:
    """Mediana, kwartyle i wartości odstające; opcjonalnie osobne pudełko dla każdej kategorii."""
    numeric_values(df, column)
    fig, ax = _new_figure()
    if by:
        categorical_values(df, by)
        data = df[[column, by]].dropna()
        sns.boxplot(data=data, x=by, y=column, ax=ax, color="#4C72B0", fliersize=2)
        ax.set(xlabel=label(by))
    else:
        sns.boxplot(y=df[column].dropna(), ax=ax, color="#4C72B0", fliersize=2)
        ax.set(xlabel="")
    ax.set(title=title or f"Rozkład i wartości odstające: {label(column)}", ylabel=label(column))
    fig.tight_layout()
    return fig


def bar_figure(df: pd.DataFrame, column: str, value: str | None = None, agg: str = "mean",
               title: str | None = None) -> Figure:
    """Bez `value`: liczba rekordów w każdej kategorii (braki jako „(brak)”).
    Z `value`: średnia / mediana / suma zmiennej liczbowej w każdej kategorii."""
    series = categorical_values(df, column)
    fig, ax = _new_figure()
    if value is None:
        counts = series.astype(object).fillna("(brak)").value_counts()
        ax.bar(counts.index.astype(str), counts.values, color="#4C72B0")
        ax.set(ylabel="Liczba rekordów")
        default_title = f"Liczba rekordów: {label(column)}"
    else:
        if agg not in ("mean", "median", "sum"):
            raise ParameterError(f"Nieznana agregacja: {agg}.", "Dostępne: mean, median, sum.")
        numeric_values(df, value)
        grouped = df.dropna(subset=[column]).groupby(column)[value].agg(agg)
        ax.bar(grouped.index.astype(str), grouped.values, color="#4C72B0")
        names = {"mean": "Średnia", "median": "Mediana", "sum": "Suma"}
        ax.set(ylabel=f"{names[agg]}: {label(value)}")
        default_title = f"{names[agg]} {value} wg {column}"
    ax.set(title=title or default_title, xlabel=label(column))
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------- korelacja

def correlation_matrix(df: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
    """Korelacja między kolumnami liczbowymi (bez kolumn stałych i flag logicznych)."""
    if method not in ("pearson", "spearman"):
        raise ParameterError(f"Nieznana metoda korelacji: {method}.", "Dostępne: pearson, spearman.")
    columns = [c for c in df.columns
               if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])
               and not is_constant(df[c].dropna())]
    if len(columns) < 2:
        raise ColumnError("Do korelacji potrzebne są co najmniej 2 zmienne kolumny liczbowe.",
                          "Wczytaj dane z większą liczbą kolumn liczbowych.")
    return df[columns].corr(method=method)


def correlation_figure(df: pd.DataFrame, method: str = "pearson", title: str | None = None) -> Figure:
    corr = correlation_matrix(df, method)
    fig = Figure(figsize=(8, 6.5), dpi=100)
    ax = fig.add_subplot()
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", vmin=-1, vmax=1, square=True,
                cbar_kws={"label": "współczynnik korelacji"}, annot_kws={"size": 8}, ax=ax)
    names = {"pearson": "Pearsona", "spearman": "Spearmana"}
    ax.set(title=title or f"Macierz korelacji ({names[method]})")
    fig.tight_layout()
    return fig


def strength(r: float) -> str:
    a = abs(r)
    word = "bardzo słaba" if a < 0.2 else "słaba" if a < 0.4 else "umiarkowana" if a < 0.6 else "silna" if a < 0.8 else "bardzo silna"
    return f"{word} {'dodatnia' if r > 0 else 'ujemna'}"


def top_correlations(df: pd.DataFrame, n: int = 5, method: str = "pearson") -> pd.DataFrame:
    """Najsilniejsze pary (bez przekątnej i bez powtórzeń A-B / B-A)."""
    corr = correlation_matrix(df, method)
    pairs = []
    cols = list(corr.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            pairs.append({"kolumna_1": a, "kolumna_2": b, "r": round(corr.loc[a, b], 3)})
    table = pd.DataFrame(pairs)
    table = table.reindex(table["r"].abs().sort_values(ascending=False).index).head(n).reset_index(drop=True)
    table["sila"] = table["r"].map(strength)
    return table


def correlation_conclusions(df: pd.DataFrame, n: int = 5) -> str:
    lines = ["Najsilniejsze korelacje (Pearson):"]
    for row in top_correlations(df, n).itertuples():
        lines.append(f"- {row.kolumna_1} – {row.kolumna_2}: r = {row.r:+.2f} ({row.sila})")
    lines += [
        "",
        "Uwaga interpretacyjna: korelacja mierzy tylko współwystępowanie liniowe, NIE przyczynowość.",
        "Np. dodatnia korelacja dochodu (MedInc) i wartości domu (MedHouseVal) nie dowodzi, że jedno",
        "powoduje drugie – obie mogą zależeć od lokalizacji. Silna ujemna korelacja Latitude–Longitude",
        "wynika z kształtu Kalifornii (wybrzeże biegnie ukośnie), a nie z zależności między zmiennymi.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- przed / po

def before_after_figure(before: pd.DataFrame, after: pd.DataFrame, column: str, kind: str = "histogram") -> Figure:
    """Dwa wykresy obok siebie: dane surowe i dane po czyszczeniu (ta sama skala osi)."""
    if kind not in ("histogram", "pudelkowy"):
        raise ParameterError(f"Porównanie obsługuje histogram i pudełkowy, a nie {kind}.", "Wybierz jeden z nich.")
    values = {"PRZED": numeric_values(before, column), "PO": numeric_values(after, column)}
    fig = Figure(figsize=(10, 4.2), dpi=100)
    axes = fig.subplots(1, 2, sharey=(kind == "pudelkowy"))
    for ax, (name, data) in zip(axes, values.items()):
        if kind == "histogram":
            # skala logarytmiczna: kilkadziesiąt błędnych rekordów obok tysięcy poprawnych byłoby niewidoczne
            ax.hist(data, bins=50, color="#4C72B0" if name == "PRZED" else "#55A868", edgecolor="white",
                    linewidth=0.3, log=True)
            ax.set(xlabel=label(column), ylabel="Liczba rekordów (skala log.)")
        else:
            sns.boxplot(y=data, ax=ax, color="#4C72B0" if name == "PRZED" else "#55A868", fliersize=2)
            ax.set(ylabel=label(column))
        ax.set_title(f"{name} czyszczeniem (n = {len(data)}, max = {data.max():.4g})")
    fig.suptitle(f"{label(column)}: przed i po czyszczeniu")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------- jedna funkcja z parametrów

CHART_KINDS = {
    "histogram": histogram_figure,
    "punktowy": scatter_figure,
    "pudelkowy": box_figure,
    "slupkowy": bar_figure,
    "korelacja": correlation_figure,
}


def build_chart(df: pd.DataFrame, kind: str, **params) -> Figure:
    """Buduje wykres z parametrów, np. build_chart(df, "punktowy", x="MedInc", y="MedHouseVal").
    Z tej funkcji skorzysta GUI – wybór z listy zamienia się na nazwę i parametry."""
    if kind not in CHART_KINDS:
        raise ParameterError(f"Nieznany typ wykresu: {kind}.", f"Dostępne: {', '.join(CHART_KINDS)}.")
    try:
        return CHART_KINDS[kind](df, **params)
    except TypeError as exc:  # np. brak wymaganego parametru x/y
        raise ParameterError(f"Niepoprawne parametry wykresu „{kind}”: {exc}", "Wybierz wszystkie wymagane kolumny.") from exc


def save_figure(fig: Figure, path: str | Path) -> Path:
    path = Path(path)
    if path.suffix.lower() not in SAVE_FORMATS:
        raise ParameterError(f"Nieobsługiwany format: {path.suffix or '(brak)'}.", "Użyj .png, .pdf albo .svg.")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150 if path.suffix.lower() == ".png" else None)
    except OSError as exc:
        raise ExportError(f"Nie udało się zapisać wykresu {path.name}: {exc.strerror or exc}",
                          "Sprawdź, czy plik nie jest otwarty i czy masz prawo zapisu.") from exc
    return path
