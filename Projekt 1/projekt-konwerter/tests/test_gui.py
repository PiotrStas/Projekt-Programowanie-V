"""Testy GUI (Lab 4).

1. Logika bez okna (lista formatów, podgląd nazwy, aktywność przycisku) – działa zawsze.
2. Testy prawdziwego okna Tkinter – pomijane, gdy nie ma ekranu (np. serwer bez grafiki).
   Okienka dialogowe (messagebox) są podstawiane, żeby test nie czekał na kliknięcie.
"""

import time
from pathlib import Path

import pytest

tk = pytest.importorskip("tkinter")

from konwerter import gui  # noqa: E402

DANE = Path(__file__).resolve().parent.parent / "dane_testowe"


# ---------- logika bez okna ----------

def test_file_types_z_rejestru():
    types = gui.file_types()
    assert types[0][0] == "Wszystkie obsługiwane"
    for ext in ("csv", "json", "txt", "docx", "odt"):
        assert f"*.{ext}" in types[0][1]
    assert ("DOCX", "*.docx") in types
    assert types[-1] == ("Wszystkie pliki", "*.*")


@pytest.mark.parametrize("plik, formaty", [
    ("", []),
    ("C:/dane/raport.docx", ["odt", "pdf", "txt"]),
    ("C:/dane/RAPORT.DOCX", ["odt", "pdf", "txt"]),
    ("C:/dane/tabela.csv", ["json"]),
    ("C:/dane/program.exe", []),
])
def test_targets_for(plik, formaty):
    assert gui.targets_for(plik) == formaty


def test_planned_output():
    assert gui.planned_output("C:/a/raport.docx", "", "pdf") is None
    assert gui.planned_output("C:/a/raport.docx", "C:/wyniki", "pdf") == Path("C:/wyniki/raport.pdf")


@pytest.mark.parametrize("plik, katalog, fmt, busy, oczekiwane", [
    ("a.docx", "wyniki", "pdf", False, True),
    ("a.docx", "wyniki", "pdf", True, False),    # w trakcie konwersji
    ("", "wyniki", "pdf", False, False),          # brak pliku
    ("a.docx", "", "pdf", False, False),          # brak katalogu
    ("a.docx", "wyniki", "", False, False),       # brak formatu
    ("a.docx", "wyniki", "json", False, False),   # niedozwolona para
])
def test_can_convert(plik, katalog, fmt, busy, oczekiwane):
    assert gui.can_convert(plik, katalog, fmt, busy) is oczekiwane


def test_unsupported_message():
    msg = gui.unsupported_message("C:/x/program.exe")
    assert ".exe" in msg and "docx" in msg


# ---------- prawdziwe okno ----------

@pytest.fixture
def app():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("brak ekranu – testy okna pominięte")
    root.withdraw()
    application = gui.ConverterApp(root)
    yield application
    root.destroy()


def wait_until_done(app, timeout=60):
    end = time.time() + timeout
    while app.busy and time.time() < end:
        app.root.update()
        time.sleep(0.02)
    assert not app.busy, "konwersja nie zakończyła się w czasie"


def state(widget) -> str:
    return str(widget.cget("state"))


def test_okno_startowe(app):
    assert state(app.convert_btn) == "disabled"
    assert state(app.target_combo) == "disabled"


def test_formaty_zmieniaja_sie_z_plikiem(app, tmp_path):
    app.source_var.set(str(DANE / "sprawozdanie.docx"))
    assert list(app.target_combo.cget("values")) == ["odt", "pdf", "txt"]
    assert state(app.target_combo) == "readonly"   # tylko wybór z listy

    app.target_var.set("pdf")
    app.source_var.set(str(DANE / "studenci.csv"))  # pdf nie jest dozwolony dla csv
    assert app.target_var.get() == "json"           # jedyny format wybrany automatycznie


def test_nieobslugiwany_plik_blokuje_konwersje(app, tmp_path):
    exe = tmp_path / "program.exe"
    exe.touch()
    app.source_var.set(str(exe))
    app.outdir_var.set(str(tmp_path))
    assert state(app.target_combo) == "disabled"
    assert state(app.convert_btn) == "disabled"


def test_konwersja_w_watku_i_status(app, tmp_path):
    app.source_var.set(str(DANE / "studenci.csv"))
    app.outdir_var.set(str(tmp_path))
    assert state(app.convert_btn) == "normal"
    assert app.preview_var.get() == "Wynik: studenci.json"

    app.on_convert()
    assert state(app.convert_btn) == "disabled"     # zablokowane w trakcie
    wait_until_done(app)

    assert (tmp_path / "studenci.json").is_file()
    assert "Zapisano: studenci.json" in app.status_var.get()
    assert state(app.open_btn) == "normal"
    assert "już istnieje" in app.preview_var.get()


@pytest.mark.parametrize("odpowiedz, oczekiwany_plik", [(False, "studenci (1).json"), (True, "studenci.json")])
def test_pytanie_o_nadpisanie(app, tmp_path, monkeypatch, odpowiedz, oczekiwany_plik):
    (tmp_path / "studenci.json").write_text("stare", encoding="utf-8")
    monkeypatch.setattr(gui.messagebox, "askyesnocancel", lambda *a, **k: odpowiedz)
    app.source_var.set(str(DANE / "studenci.csv"))
    app.outdir_var.set(str(tmp_path))

    app.on_convert()
    wait_until_done(app)

    assert "Żółkiewski" in (tmp_path / oczekiwany_plik).read_text(encoding="utf-8")
    if not odpowiedz:
        assert (tmp_path / "studenci.json").read_text(encoding="utf-8") == "stare"


def test_anulowanie_nadpisania(app, tmp_path, monkeypatch):
    (tmp_path / "studenci.json").write_text("stare", encoding="utf-8")
    monkeypatch.setattr(gui.messagebox, "askyesnocancel", lambda *a, **k: None)
    app.source_var.set(str(DANE / "studenci.csv"))
    app.outdir_var.set(str(tmp_path))

    app.on_convert()

    assert not app.busy
    assert sorted(p.name for p in tmp_path.iterdir()) == ["studenci.json"]
    assert app.status_var.get() == "Anulowano."


def test_blad_pokazuje_komunikat(app, tmp_path, monkeypatch):
    shown = []
    monkeypatch.setattr(gui.messagebox, "showerror", lambda title, text: shown.append(text))
    app.source_var.set(str(DANE / "bledny.json"))
    app.outdir_var.set(str(tmp_path))

    app.on_convert()
    wait_until_done(app)

    assert "Niepoprawny JSON" in shown[0] and "Co zrobić" in shown[0]
    assert app.status_var.get().startswith("✖")
    assert state(app.convert_btn) == "normal"       # można spróbować ponownie
    assert list(tmp_path.iterdir()) == []


def test_plik_usuniety_po_wybraniu(app, tmp_path, monkeypatch):
    shown = []
    monkeypatch.setattr(gui.messagebox, "showerror", lambda title, text: shown.append(text))
    src = tmp_path / "dane.csv"
    src.write_text("a\n1\n", encoding="utf-8")
    app.source_var.set(str(src))
    app.outdir_var.set(str(tmp_path))
    src.unlink()

    app.on_convert()

    assert not app.busy
    assert "Nie znaleziono pliku" in shown[0]
