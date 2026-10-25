"""Testy Grupy C (LibreOffice).

Testy z prawdziwym LibreOffice są pomijane (SKIPPED), jeśli program nie jest zainstalowany.
Wykrywanie narzędzia i obsługa błędów procesu są testowane zawsze – na podstawionym subprocess.run.
"""

import subprocess
from pathlib import Path

import pytest

from konwerter.converters import office
from konwerter.core import ConversionRequest, execute
from konwerter.errors import ConversionError, InvalidInputError, MissingDependencyError

DANE = Path(__file__).resolve().parent.parent / "dane_testowe"


def libreoffice_installed() -> bool:
    try:
        office.find_soffice()
        return True
    except MissingDependencyError:
        return False


needs_lo = pytest.mark.skipif(not libreoffice_installed(), reason="LibreOffice nie jest zainstalowany")


# ---------- wykrywanie narzędzia (zawsze) ----------

def test_brak_libreoffice_przez_konfiguracje(tmp_path, monkeypatch):
    """Minimalna macierz testów: 'Brak LibreOffice' – test przez zmianę konfiguracji."""
    monkeypatch.setenv(office.ENV_VAR, str(tmp_path / "nie_ma_soffice.exe"))
    with pytest.raises(MissingDependencyError, match="nieistniejący plik") as info:
        office.find_soffice()
    assert "libreoffice.org" in info.value.hint


def test_brak_libreoffice_w_systemie(monkeypatch):
    monkeypatch.delenv(office.ENV_VAR, raising=False)
    monkeypatch.setattr(office.shutil, "which", lambda name: None)
    monkeypatch.setattr(office, "CANDIDATES", [])
    with pytest.raises(MissingDependencyError, match="Nie znaleziono"):
        office.find_soffice()


def test_brak_libreoffice_przez_execute_nie_zostawia_plikow(tmp_path, monkeypatch):
    monkeypatch.setenv(office.ENV_VAR, str(tmp_path / "brak.exe"))
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(MissingDependencyError):
        execute(ConversionRequest(DANE / "sprawozdanie.docx", "pdf", out))
    assert list(out.iterdir()) == []


def test_zmienna_srodowiskowa_ma_pierwszenstwo(tmp_path, monkeypatch):
    fake = tmp_path / "soffice.exe"
    fake.touch()
    monkeypatch.setenv(office.ENV_VAR, str(fake))
    assert office.find_soffice() == fake


def test_polecenie_jest_lista_bez_powloki(tmp_path):
    cmd = office.build_command(Path("soffice"), Path("mój plik.docx"), "pdf", tmp_path, tmp_path / "p")
    assert isinstance(cmd, list)
    assert "--headless" in cmd
    assert cmd[cmd.index("--convert-to") + 1] == "pdf"
    assert cmd[-1].endswith("mój plik.docx")   # nazwa ze spacją to jeden argument


# ---------- obsługa wyniku procesu (podstawiony subprocess.run) ----------

@pytest.fixture
def fake_soffice(tmp_path, monkeypatch):
    fake = tmp_path / "soffice.exe"
    fake.touch()
    monkeypatch.setenv(office.ENV_VAR, str(fake))


def test_niezerowy_kod_zakonczenia(tmp_path, monkeypatch, fake_soffice):
    def run(cmd, **kwargs):
        assert "shell" not in kwargs          # nigdy shell=True
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="Error: source file could not be loaded")

    monkeypatch.setattr(office.subprocess, "run", run)
    with pytest.raises(ConversionError, match="could not be loaded"):
        office.convert_with_libreoffice(DANE / "sprawozdanie.docx", tmp_path / "x.pdf", "pdf")


def test_kod_zero_ale_brak_pliku(tmp_path, monkeypatch, fake_soffice):
    monkeypatch.setattr(office.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, "", ""))
    with pytest.raises(InvalidInputError, match="nie utworzył"):
        office.convert_with_libreoffice(DANE / "sprawozdanie.docx", tmp_path / "x.pdf", "pdf")


def test_przekroczony_czas(tmp_path, monkeypatch, fake_soffice):
    def run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    monkeypatch.setattr(office.subprocess, "run", run)
    with pytest.raises(ConversionError, match="nie zakończył"):
        office.convert_with_libreoffice(DANE / "sprawozdanie.docx", tmp_path / "x.pdf", "pdf")


# ---------- prawdziwy LibreOffice ----------

@needs_lo
@pytest.mark.parametrize("src, fmt, magic", [
    ("sprawozdanie.docx", "pdf", b"%PDF"),
    ("sprawozdanie.odt", "pdf", b"%PDF"),
    ("sprawozdanie.docx", "odt", b"PK"),
    ("sprawozdanie.odt", "docx", b"PK"),
])
def test_libreoffice_konwersje(tmp_path, src, fmt, magic):
    wynik = execute(ConversionRequest(DANE / src, fmt, tmp_path))
    assert wynik == tmp_path / f"sprawozdanie.{fmt}"
    assert wynik.read_bytes().startswith(magic)


@needs_lo
def test_libreoffice_tresc_zachowana(tmp_path):
    """DOCX -> ODT -> DOCX: tekst i polskie znaki przetrwały."""
    import docx

    odt = execute(ConversionRequest(DANE / "sprawozdanie.docx", "odt", tmp_path))
    back = execute(ConversionRequest(odt, "docx", tmp_path, overwrite=False))
    tekst = "\n".join(p.text for p in docx.Document(str(back)).paragraphs)
    assert "ąćęłńóśźż" in tekst
    assert "Sprawozdanie z laboratorium" in tekst


def test_uszkodzony_plik_odrzucony_przed_uruchomieniem(tmp_path):
    with pytest.raises(InvalidInputError, match="uszkodzony"):
        execute(ConversionRequest(DANE / "uszkodzony.docx", "pdf", tmp_path))
    assert list(tmp_path.iterdir()) == []
