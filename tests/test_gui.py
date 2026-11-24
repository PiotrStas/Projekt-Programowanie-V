"""Lab 8: logika okna (bez Tkintera) i testy prawdziwego okna.

Testy okna są pomijane, gdy nie ma Tkintera albo ekranu. Okienka dialogowe (messagebox)
są podstawiane, żeby test nie czekał na kliknięcie.
"""

import pandas as pd
import pytest

from studio import gui_logic as logic
from studio.errors import ColumnError, ParameterError
from studio.session import DataSession


# ================================================================ logika bez okna

def test_kolumny_dopasowane_do_operacji(small_df):
    assert logic.valid_columns(small_df, "fill", "mediana") == ["id", "wiek", "pokoje"]      # bez tekstu
    assert "region" in logic.valid_columns(small_df, "fill", "dominanta (najczęstsza wartość)")
    assert logic.valid_columns(small_df, "range") == ["id", "wiek", "pokoje"]
    assert logic.valid_columns(small_df, "duplicates")[0] == logic.ALL_COLUMNS
    assert logic.valid_columns(small_df, "drop_missing")[0] == logic.ANY_COLUMN
    assert logic.valid_columns(None, "fill") == []                                         # brak danych


def test_flaga_odstajacych_nie_trafia_na_liste(small_df):
    flagged = small_df.assign(pokoje_odstajaca=[False] * 8)
    assert "pokoje_odstajaca" not in logic.valid_columns(flagged, "duplicates")


@pytest.mark.parametrize("tekst, wynik", [("1.5", 1.5), ("2,5", 2.5), (" -5 ", -5.0), ("", None)])
def test_parse_number(tekst, wynik):
    assert logic.parse_number(tekst, "x", required=False) == wynik


@pytest.mark.parametrize("tekst", ["abc", "nan", "inf"])
def test_parse_number_bledy(tekst):
    with pytest.raises(ParameterError):
        logic.parse_number(tekst, "x")


def test_parse_number_wymagana():
    with pytest.raises(ParameterError, match="Nie podano"):
        logic.parse_number("", "minimum")


def test_run_operation_wszystkie_rodzaje(small_df):
    s = DataSession(small_df)
    assert logic.run_operation(s, "duplicates", logic.ALL_COLUMNS, "", {}).zmienione_rekordy == 1
    assert logic.run_operation(s, "range", "wiek", "zamień na brak", {"min": "0", "max": "100"}).zmienione_rekordy == 1
    assert logic.run_operation(s, "fill", "wiek", "mediana", {}).zmienione_rekordy == 2
    assert logic.run_operation(s, "fill", "region", "stała wartość", {"value": "brak"}).zmienione_rekordy == 1
    assert logic.run_operation(s, "outliers", "pokoje", "tylko oznacz (nowa kolumna)", {"factor": "1,5"}).zmienione_rekordy == 1
    assert logic.run_operation(s, "drop_missing", logic.ANY_COLUMN, "", {}).zmienione_rekordy == 0
    assert len(s.log) == 6


@pytest.mark.parametrize("operacja, kolumna, wariant, parametry, blad", [
    ("fill", "", "mediana", {}, ParameterError),                          # brak kolumny
    ("fill", "wiek", "", {}, ParameterError),                             # brak wariantu
    ("fill", "region", "mediana", {}, ColumnError),                       # mediana z tekstu
    ("range", "wiek", "zamień na brak", {"min": "abc"}, ParameterError),   # zła liczba
    ("range", "wiek", "zamień na brak", {"min": "10", "max": "0"}, ParameterError),  # min > max
    ("outliers", "wiek", "usuń wiersze", {"factor": "-1"}, ParameterError),
])
def test_run_operation_bledy_nie_zmieniaja_danych(small_df, operacja, kolumna, wariant, parametry, blad):
    s = DataSession(small_df)
    with pytest.raises(blad):
        logic.run_operation(s, operacja, kolumna, wariant, parametry)
    pd.testing.assert_frame_equal(s.current, small_df)
    assert s.log == []


def test_preview_rows(small_df):
    rows = logic.preview_rows(small_df, limit=3)
    assert len(rows) == 3
    assert rows[0] == ("1", "10", "4", "A")
    assert logic.preview_rows(small_df)[3][3] == ""                       # brak -> pusty tekst


# ================================================================ prawdziwe okno

@pytest.fixture
def app(monkeypatch):
    tk = pytest.importorskip("tkinter")       # tylko testy okna wymagają Tkintera
    from studio import gui

    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("brak ekranu – testy okna pominięte")
    root.withdraw()
    errors: list[str] = []
    monkeypatch.setattr(gui.messagebox, "showerror", lambda title, text: errors.append(text))
    application = gui.StudioApp(root)
    application.errors = errors
    yield application
    root.destroy()


def state(widget) -> str:
    return str(widget.cget("state"))


def test_start_bez_danych(app):
    assert app.session is None
    assert state(app.apply_btn) == "disabled" and state(app.reset_btn) == "disabled"


def test_wczytanie_i_profil(app, dane):
    assert app.load_file(dane / "test_03_braki_duplikaty.csv")
    assert state(app.apply_btn) == "normal"
    assert len(app.preview_tree.get_children()) == 5
    assert len(app.profile_tree.get_children()) == 3                      # 3 kolumny
    assert "Pełne duplikaty: 1" in app.summary_label.cget("text")


def test_bledny_plik_nie_zamyka_aplikacji(app, dane):
    app.load_file(dane / "test_01_przecinek.csv")
    assert not app.load_file(dane / "test_05_bledne_wiersze.csv")
    assert "Wadliwy wiersz 3" in app.errors[0]
    assert app.session.source == "test_01_przecinek.csv"                   # poprzednie dane zostały


def test_listy_kolumn_odswiezaja_sie_po_zmianie_zbioru(app, dane):
    app.load_file(dane / "test_04_zakres_outlier.csv")
    app.op_var.set(logic.OPERATIONS["range"].label)
    app.on_operation_change()
    assert list(app.column_combo.cget("values")) == ["id", "HouseAge", "AveRooms"]
    app.column_var.set("HouseAge")

    app.load_file(dane / "test_01_przecinek.csv")                          # inny zbiór
    assert list(app.column_combo.cget("values")) == ["id", "value"]
    assert app.column_var.get() == ""                                      # stary wybór wyczyszczony


def test_operacja_dziennik_i_reset(app, dane):
    app.load_file(dane / "test_03_braki_duplikaty.csv")
    app.op_var.set(logic.OPERATIONS["duplicates"].label)
    app.on_operation_change()
    app.apply_operation()
    assert len(app.session.current) == 4
    assert len(app.log_tree.get_children()) == 2                           # wczytanie + duplikaty
    app.reset()
    assert len(app.session.current) == 5
    assert len(app.log_tree.get_children()) == 3


def test_zly_parametr_pokazuje_blad(app, dane):
    app.load_file(dane / "test_04_zakres_outlier.csv")
    app.op_var.set(logic.OPERATIONS["range"].label)
    app.on_operation_change()
    app.column_var.set("HouseAge")
    app.param_vars["min"].set("dziesięć")
    app.apply_operation()
    assert "nie jest liczbą" in app.errors[0]
    assert len(app.session.log) == 1                                       # tylko wczytanie


def test_raport_jakosci_w_oknie(app, dane):
    app.load_file(dane / "test_04_zakres_outlier.csv")
    app.q_column_var.set("HouseAge")
    app.q_min_var.set("0")
    app.check_quality()
    rows = [app.quality_tree.item(i, "values") for i in app.quality_tree.get_children()]
    assert rows[0][0] == "zakres" and rows[0][3] == "1"


def test_kolumny_do_wykresow(dane):
    from studio.loader import load_csv

    df, _ = load_csv(dane / "test_06_stala_tekst.csv")
    assert logic.chart_numeric_columns(df) == ["id"]                         # stała kolumna pominięta
    assert logic.chart_category_columns(df) == ["label"]
    assert logic.chart_choices(df, "punktowy") == [["id"], ["id"], [logic.NONE, "label"]]
    assert logic.chart_choices(df, "korelacja") == []


def test_parametry_wykresu():
    assert logic.chart_params("punktowy", ["a", "b", logic.NONE]) == {"x": "a", "y": "b"}
    assert logic.chart_params("slupkowy", ["Region", "cena"]) == {"column": "Region", "value": "cena", "agg": "median"}
    assert logic.chart_params("korelacja", []) == {}
    with pytest.raises(ParameterError, match="Oś Y"):
        logic.chart_params("punktowy", ["a", ""])


def test_wykres_w_oknie_i_podmiana(app, dane):
    app.load_file(dane / "test_04_zakres_outlier.csv")
    app.chart_type_var.set("Histogram")
    app.refresh_chart_columns()
    app.chart_col_vars[0].set("AveRooms")
    app.draw_chart()
    first = app.canvas
    assert first is not None and str(app.save_chart_btn.cget("state")) == "normal"

    app.chart_type_var.set("Wykres pudełkowy")
    app.refresh_chart_columns()
    app.chart_col_vars[0].set("HouseAge")
    app.draw_chart()
    assert app.canvas is not first
    canvases = [w for w in app.chart_frame.winfo_children() if w.winfo_class() == "Canvas"]
    assert len(canvases) == 1                                                # stary wykres usunięty


def test_stala_kolumna_blokuje_wykres(app, dane):
    app.load_file(dane / "test_06_stala_tekst.csv")
    app.chart_type_var.set("Histogram")
    app.refresh_chart_columns()
    assert "constant" not in app.chart_combos[0].cget("values")
    app.chart_col_vars[0].set("constant")
    app.draw_chart()
    assert "stała" in app.errors[0]
    assert app.canvas is None


def test_zmiana_danych_czysci_wykres(app, dane):
    app.load_file(dane / "test_04_zakres_outlier.csv")
    app.draw_chart()
    assert app.canvas is not None
    app.reset()
    assert app.canvas is None and "Dane się zmieniły" in app.chart_info.cget("text")


def test_eksport_z_okna(app, dane, tmp_path):
    from studio.loader import load_csv

    app.load_file(dane / "test_03_braki_duplikaty.csv")
    app.apply_operation()                                                    # domyślnie: usuń duplikaty
    reloaded, _ = load_csv(app.export_csv(tmp_path / "cleaned.csv"))
    assert reloaded.shape == (4, 3)
    log, _ = load_csv(app.export_log(tmp_path / "raport_zmian.csv"))
    assert log["nazwa"].tolist() == ["wczytanie", "usuniecie_duplikatow"]

    app.chart_type_var.set("Wykres słupkowy")
    app.refresh_chart_columns()
    app.draw_chart()
    for ext, start in ((".png", b"\x89PNG"), (".pdf", b"%PDF"), (".svg", b"<?xml")):
        assert app.save_chart(tmp_path / f"wykres{ext}").read_bytes().startswith(start)


def test_blad_zapisu_w_oknie(app, dane, tmp_path):
    app.load_file(dane / "test_01_przecinek.csv")
    assert app.export_csv(tmp_path) is None                                  # katalog zamiast pliku
    assert "Nie udało się zapisać" in app.errors[0]
