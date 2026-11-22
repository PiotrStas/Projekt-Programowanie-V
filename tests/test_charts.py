"""Wykresy: poprawne typy, opisy osi, blokada złych kolumn, zapis do plików."""

import pandas as pd
import pytest
from matplotlib.figure import Figure

from studio import charts
from studio.errors import ColumnError, ParameterError
from studio.loader import load_csv


@pytest.fixture
def df() -> pd.DataFrame:
    return pd.DataFrame({
        "dochod": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "cena":   [1.5, 2.1, 3.2, 3.9, 5.1, 6.3],
        "stala":  [5, 5, 5, 5, 5, 5],
        "region": ["A", "B", "A", None, "C", "B"],
        "id":     ["x1", "x2", "x3", "x4", "x5", "x6"],
    })


def axis_texts(fig: Figure) -> tuple[str, str, str]:
    ax = fig.axes[0]
    return ax.get_title(), ax.get_xlabel(), ax.get_ylabel()


# ---------- cztery typy + korelacja ----------

def test_histogram(df):
    title, xlabel, ylabel = axis_texts(charts.histogram_figure(df, "dochod"))
    assert "dochod" in title and xlabel == "dochod" and ylabel == "Liczba rekordów"


def test_punktowy_z_korelacja(df):
    title, xlabel, ylabel = axis_texts(charts.scatter_figure(df, "dochod", "cena"))
    assert (xlabel, ylabel) == ("dochod", "cena")
    assert "r = 0.99" in title or "r = 1.00" in title


def test_pudelkowy_z_grupami(df):
    fig = charts.box_figure(df, "cena", by="region")
    assert axis_texts(fig)[1] == "region"


def test_slupkowy_liczebnosc_z_brakami(df):
    fig = charts.bar_figure(df, "region")
    labels = [t.get_text() for t in fig.axes[0].get_xticklabels()]
    assert set(labels) == {"A", "B", "C", "(brak)"}


def test_slupkowy_agregacja(df):
    fig = charts.bar_figure(df, "region", value="cena", agg="median")
    assert axis_texts(fig)[2].startswith("Mediana")


def test_opisy_osi_california(dane):
    data, _ = load_csv(dane / "test_04_zakres_outlier.csv")
    _, xlabel, _ = axis_texts(charts.histogram_figure(data, "HouseAge"))
    assert xlabel == "Mediana wieku budynków [lata]"


def test_korelacja(df):
    corr = charts.correlation_matrix(df)
    assert list(corr.columns) == ["dochod", "cena"]          # bez kolumny stałej i tekstowej
    top = charts.top_correlations(df)
    assert top.loc[0, "sila"] == "bardzo silna dodatnia"
    assert isinstance(charts.correlation_figure(df), Figure)
    assert "przyczynowość" in charts.correlation_conclusions(df)


# ---------- blokada niepoprawnych wykresów ----------

@pytest.mark.parametrize("funkcja, kolumna, fragment", [
    (charts.histogram_figure, "region", "nie jest liczbowa"),
    (charts.histogram_figure, "stala", "jest stała"),
    (charts.box_figure, "id", "nie jest liczbowa"),
    (charts.histogram_figure, "nie_ma", "Brak kolumny"),
])
def test_zla_kolumna_blokuje_wykres(df, funkcja, kolumna, fragment):
    with pytest.raises(ColumnError, match=fragment) as info:
        funkcja(df, kolumna)
    assert info.value.hint                                    # komunikat ma podpowiedź


def test_plik_ze_stala_kolumna(dane):
    data, _ = load_csv(dane / "test_06_stala_tekst.csv")
    with pytest.raises(ColumnError, match="stała"):
        charts.histogram_figure(data, "constant")
    with pytest.raises(ColumnError, match="nie jest liczbowa"):
        charts.histogram_figure(data, "label")


def test_punktowy_ta_sama_kolumna(df):
    with pytest.raises(ParameterError, match="ta sama"):
        charts.scatter_figure(df, "cena", "cena")


def test_slupkowy_za_duzo_kategorii():
    data = pd.DataFrame({"x": [str(i) for i in range(40)]})
    with pytest.raises(ColumnError, match="za dużo"):
        charts.bar_figure(data, "x")


def test_korelacja_za_malo_kolumn(df):
    with pytest.raises(ColumnError, match="co najmniej 2"):
        charts.correlation_matrix(df[["dochod", "stala", "region"]])


# ---------- funkcja z parametrów, przed/po, zapis ----------

def test_build_chart(df):
    assert isinstance(charts.build_chart(df, "punktowy", x="dochod", y="cena"), Figure)
    with pytest.raises(ParameterError, match="Nieznany typ"):
        charts.build_chart(df, "kolowy")
    with pytest.raises(ParameterError, match="Niepoprawne parametry"):
        charts.build_chart(df, "punktowy", x="dochod")       # brak y


def test_przed_po(df):
    after = df.assign(cena=df["cena"].clip(upper=5))
    fig = charts.before_after_figure(df, after, "cena", "histogram")
    assert len(fig.axes) == 2
    assert fig.axes[0].get_title().startswith("PRZED") and fig.axes[1].get_title().startswith("PO")


@pytest.mark.parametrize("rozszerzenie, poczatek", [(".png", b"\x89PNG"), (".pdf", b"%PDF"), (".svg", b"<?xml")])
def test_zapis_wykresu(df, tmp_path, rozszerzenie, poczatek):
    path = charts.save_figure(charts.histogram_figure(df, "cena"), tmp_path / f"wykres{rozszerzenie}")
    assert path.read_bytes().startswith(poczatek)


def test_zapis_zly_format(df, tmp_path):
    with pytest.raises(ParameterError, match="format"):
        charts.save_figure(charts.histogram_figure(df, "cena"), tmp_path / "wykres.jpg")
