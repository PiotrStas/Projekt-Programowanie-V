"""Profil danych i reguły jakości (zakres, IQR)."""

import pandas as pd
import pytest

from studio import profile
from studio.errors import ColumnError, ParameterError
from studio.loader import load_csv
from studio.rules import RangeRule, iqr_bounds, iqr_mask, quality_report


# ---------- profil ----------

def test_profil_braki_i_duplikaty(dane):
    df, _ = load_csv(dane / "test_03_braki_duplikaty.csv")
    s = profile.summary(df)
    assert (s["wiersze"], s["kolumny"]) == (5, 3)
    assert s["pelne_duplikaty"] == 1          # wiersze 2,,B występują dwa razy
    assert s["braki"] == 3                    # 2× value, 1× group
    assert s["wiersze_z_brakami"] == 3

    cols = profile.column_profile(df)
    assert cols.loc["value", "braki"] == 2
    assert cols.loc["value", "braki_pct"] == 40.0
    assert cols.loc["group", "braki"] == 1
    assert cols.loc["group", "unikalne"] == 3
    assert cols.loc["id", "unikalne"] == 4


def test_profil_statystyki(small_df):
    cols = profile.column_profile(small_df)
    assert cols.loc["pokoje", "max"] == 1000
    assert cols.loc["pokoje", "mediana"] == 5
    assert cols.loc["region", "najczestsza"] in ("A", "B")
    assert pd.isna(cols.loc["region", "srednia"])      # dla tekstu brak statystyk liczbowych


def test_typy_kolumn_i_stala(dane):
    df, _ = load_csv(dane / "test_06_stala_tekst.csv")
    assert profile.numeric_columns(df) == ["id", "constant"]
    assert profile.categorical_columns(df) == ["label"]
    assert profile.is_constant(df["constant"])
    assert not profile.is_constant(df["id"])


def test_profil_nie_zmienia_danych(small_df):
    before = small_df.copy()
    profile.summary(small_df)
    profile.column_profile(small_df)
    pd.testing.assert_frame_equal(small_df, before)


# ---------- reguła zakresu ----------

def test_regula_zakresu_wykrywa_rekord(dane):
    df, _ = load_csv(dane / "test_04_zakres_outlier.csv")
    mask = RangeRule("HouseAge", 0, 100).violations(df)
    assert df.loc[mask, "id"].tolist() == [2]


def test_brak_nie_jest_naruszeniem(small_df):
    mask = RangeRule("wiek", 0, 100).violations(small_df)
    assert mask.sum() == 2                    # dwa razy -5; brak (None) nie liczy się jako naruszenie


def test_jedna_granica(small_df):
    assert RangeRule("pokoje", maximum=100).violations(small_df).sum() == 1


@pytest.mark.parametrize("regula, blad", [
    (RangeRule("wiek", 10, 0), ParameterError),          # min > max
    (RangeRule("wiek"), ParameterError),                 # brak granic
    (RangeRule("region", 0, 1), ColumnError),            # kolumna tekstowa
    (RangeRule("nie_ma", 0, 1), ColumnError),            # brak kolumny
])
def test_niepoprawne_parametry_reguly(small_df, regula, blad):
    with pytest.raises(blad):
        regula.validate(small_df)


# ---------- IQR ----------

def test_iqr_wykrywa_outlier(dane):
    df, _ = load_csv(dane / "test_04_zakres_outlier.csv")
    mask = iqr_mask(df, "AveRooms")
    assert df.loc[mask, "id"].tolist() == [4]            # AveRooms = 1000


def test_iqr_stala_kolumna_nic_nie_wykrywa(dane):
    df, _ = load_csv(dane / "test_06_stala_tekst.csv")
    assert iqr_bounds(df, "constant") is None
    assert not iqr_mask(df, "constant").any()


def test_iqr_zly_wspolczynnik(small_df):
    with pytest.raises(ParameterError):
        iqr_bounds(small_df, "pokoje", factor=0)


def test_iqr_kolumna_tekstowa(small_df):
    with pytest.raises(ColumnError, match="nie jest liczbowa"):
        iqr_mask(small_df, "region")


def test_raport_jakosci(dane):
    df, _ = load_csv(dane / "test_04_zakres_outlier.csv")
    before = df.copy()
    report = quality_report(df, [RangeRule("HouseAge", 0, 100)], ["AveRooms"])
    assert report["naruszenia"].tolist() == [1, 1]
    assert report["regula"].tolist() == ["zakres", "IQR"]
    pd.testing.assert_frame_equal(df, before)            # raport nie zmienia danych
