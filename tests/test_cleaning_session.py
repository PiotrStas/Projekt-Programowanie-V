"""Operacje czyszczenia, sesja (raw/current/reset), dziennik zmian, eksport i pipeline."""

import pandas as pd
import pytest

from studio import cleaning
from studio.errors import ColumnError, ExportError, ParameterError
from studio.loader import load_csv
from studio.pipeline import run
from studio.rules import RangeRule
from studio.session import DataSession


def other_columns_unchanged(before: pd.DataFrame, after: pd.DataFrame, changed: str) -> None:
    """Operacja na jednej kolumnie nie może zmienić pozostałych."""
    others = [c for c in before.columns if c != changed]
    pd.testing.assert_frame_equal(before[others], after[others])


# ---------- duplikaty ----------

def test_pelne_duplikaty_kontrolowana_para(small_df):
    result, removed = cleaning.drop_duplicates(small_df)
    assert removed == 1
    assert result["id"].tolist() == [1, 2, 3, 4, 5, 6, 7]     # zostaje pierwsze wystąpienie


def test_duplikaty_wedlug_klucza():
    df = pd.DataFrame({"id": [1, 1, 2], "v": [10, 99, 20]})   # nie są pełnymi duplikatami
    assert cleaning.drop_duplicates(df)[1] == 0
    result, removed = cleaning.drop_duplicates(df, subset=["id"])
    assert removed == 1 and result["v"].tolist() == [10, 20]


# ---------- braki ----------

@pytest.mark.parametrize("strategia, wartosc_oczekiwana", [("median", 30.0), ("mean", 25.0), ("constant", 0.0)])
def test_uzupelnianie_liczb(strategia, wartosc_oczekiwana):
    df = pd.DataFrame({"x": [10.0, None, 30.0, 35.0], "y": ["a", "b", None, "d"]})
    result, filled = cleaning.fill_missing(df, "x", strategia, value=0 if strategia == "constant" else None)
    assert filled == 1
    assert result.loc[1, "x"] == pytest.approx(wartosc_oczekiwana)
    other_columns_unchanged(df, result, "x")
    assert df["x"].isna().sum() == 1                          # oryginał nietknięty


def test_uzupelnianie_tekstu_dominanta(small_df):
    result, filled = cleaning.fill_missing(small_df, "region", "mode")
    assert filled == 1
    assert result["region"].isna().sum() == 0
    other_columns_unchanged(small_df, result, "region")


def test_mediana_dla_tekstu_to_blad(small_df):
    with pytest.raises(ColumnError, match="nie jest liczbowa"):
        cleaning.fill_missing(small_df, "region", "median")


@pytest.mark.parametrize("strategia, wartosc", [("magia", None), ("constant", None), ("constant", "abc")])
def test_zle_parametry_uzupelniania(small_df, strategia, wartosc):
    with pytest.raises(ParameterError):
        cleaning.fill_missing(small_df, "wiek", strategia, wartosc)


def test_usuwanie_brakow(small_df):
    result, removed = cleaning.drop_missing(small_df, ["region"])
    assert removed == 1 and len(result) == 7
    assert cleaning.drop_missing(small_df)[1] == 2            # brak w dowolnej kolumnie


# ---------- zakres ----------

@pytest.mark.parametrize("akcja, wiersze, wiek_id2", [("set_missing", 8, None), ("clip", 8, 0.0), ("drop", 6, "brak")])
def test_akcje_reguly_zakresu(small_df, akcja, wiersze, wiek_id2):
    result, changed = cleaning.apply_range_rule(small_df, RangeRule("wiek", 0, 100), akcja)
    assert changed == 2 and len(result) == wiersze
    values = result.loc[result["id"] == 2, "wiek"]
    if wiek_id2 is None:
        assert values.isna().all()
    elif wiek_id2 == "brak":
        assert values.empty
    else:
        assert (values == wiek_id2).all()
    if akcja != "drop":
        other_columns_unchanged(small_df, result, "wiek")


# ---------- wartości odstające ----------

def test_outlier_oznaczenie_nie_zmienia_danych(small_df):
    result, count = cleaning.handle_outliers(small_df, "pokoje", "flag")
    assert count == 1
    assert result.loc[result["pokoje_odstajaca"], "pokoje"].tolist() == [1000.0]
    pd.testing.assert_frame_equal(result[small_df.columns], small_df)


def test_outlier_przyciecie_i_usuniecie(small_df):
    clipped, _ = cleaning.handle_outliers(small_df, "pokoje", "clip")
    assert clipped["pokoje"].max() < 1000
    other_columns_unchanged(small_df, clipped, "pokoje")
    dropped, count = cleaning.handle_outliers(small_df, "pokoje", "drop")
    assert count == 1 and 1000.0 not in dropped["pokoje"].tolist()


# ---------- sesja ----------

def test_sesja_raw_nietkniete_i_dziennik(small_df):
    session = DataSession(small_df)
    session.drop_duplicates()
    session.apply_range_rule(RangeRule("wiek", 0, 100))
    session.fill_missing("wiek", "median")

    pd.testing.assert_frame_equal(session.raw, small_df)
    log = session.log_frame()
    assert log["nazwa"].tolist() == ["usuniecie_duplikatow", "regula_zakresu", "uzupelnienie_brakow"]
    assert log["zmienione_rekordy"].tolist() == [1, 1, 2]       # 1 duplikat, 1×-5 po deduplikacji, 2 braki
    assert log.loc[0, "wiersze_przed"] == 8 and log.loc[0, "wiersze_po"] == 7


def test_reset_bez_ponownego_wczytania(small_df):
    session = DataSession(small_df)
    session.drop_missing()
    assert len(session.current) == 6
    session.reset()
    pd.testing.assert_frame_equal(session.current, small_df)
    assert session.log[-1].nazwa == "reset"


def test_blad_operacji_nie_zmienia_stanu(small_df):
    session = DataSession(small_df)
    with pytest.raises(ColumnError):
        session.fill_missing("region", "median")
    pd.testing.assert_frame_equal(session.current, small_df)
    assert session.log == []


def test_eksport_mozna_ponownie_wczytac(dane, tmp_path):
    session = DataSession.from_csv(dane / "test_03_braki_duplikaty.csv")
    session.drop_duplicates()
    path = session.export_cleaned(tmp_path / "cleaned.csv")
    reloaded, _ = load_csv(path)
    assert reloaded.shape == (4, 3)
    assert reloaded["group"].isna().sum() == 1
    log, _ = load_csv(session.export_log(tmp_path / "raport.csv"))
    assert log["nazwa"].tolist() == ["wczytanie", "usuniecie_duplikatow"]


def test_blad_zapisu(small_df, tmp_path):
    with pytest.raises(ExportError, match="Nie udało się zapisać"):
        DataSession(small_df).export_cleaned(tmp_path)        # katalog zamiast pliku


# ---------- pipeline na zbiorze referencyjnym ----------

def test_pipeline_california(dane, tmp_path):
    session = run(dane / "california_housing_z_problemami.csv", tmp_path)
    changes = dict(zip(session.log_frame()["parametry"], session.log_frame()["zmienione_rekordy"]))
    assert changes["pełne duplikaty"] == 30
    assert changes["HouseAge ∈ [0, 100], akcja=set_missing"] == 40
    assert changes["AveRooms ∈ [0, 200], akcja=set_missing"] == 50
    assert changes["kolumna=MedInc, strategia=median"] == 80
    assert changes["kolumny=['Region']"] == 40
    assert len(session.current) == 20600
    assert session.current.drop(columns=["AveOccup_odstajaca", "Population_odstajaca"]).isna().sum().sum() == 0
    for name in ("cleaned.csv", "raport_zmian.csv", "profil_przed.csv", "profil_po.csv", "raport.txt"):
        assert (tmp_path / name).is_file()


def test_pipeline_powtarzalny(dane, tmp_path):
    run(dane / "california_housing_z_problemami.csv", tmp_path / "a")
    run(dane / "california_housing_z_problemami.csv", tmp_path / "b")
    assert (tmp_path / "a" / "cleaned.csv").read_bytes() == (tmp_path / "b" / "cleaned.csv").read_bytes()
