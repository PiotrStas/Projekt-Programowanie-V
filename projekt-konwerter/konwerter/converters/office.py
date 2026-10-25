"""Grupa C – formaty biurowe przez LibreOffice w trybie bez interfejsu (headless).

Kierunki: DOCX -> PDF, ODT -> PDF, DOCX -> ODT, ODT -> DOCX.

Jak to działa:
1. find_soffice() szuka programu LibreOffice (zmienna KONWERTER_SOFFICE, PATH, typowe ścieżki),
2. LibreOffice zapisuje wynik do katalogu tymczasowego (sam nadpisałby plik bez pytania!),
3. sprawdzamy kod zakończenia i to, czy plik naprawdę powstał,
4. przenosimy wynik pod ścieżkę wskazaną przez execute() – polityka nadpisywania zostaje w core.py.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from ..core import converter
from ..errors import ConversionError, InvalidInputError, MissingDependencyError

ENV_VAR = "KONWERTER_SOFFICE"   # pozwala wskazać własną ścieżkę (i przetestować brak narzędzia)
TIMEOUT_S = 120
# Osobny profil LibreOffice w katalogu tymczasowym systemu. Tworzy się przy pierwszej
# konwersji (dlatego pierwsza trwa dłużej), kolejne korzystają z gotowego.
PROFILE_DIR = Path(tempfile.gettempdir()) / "konwerter_libreoffice_profil"

if sys.platform == "win32":
    CANDIDATES = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "LibreOffice/program/soffice.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "LibreOffice/program/soffice.exe",
    ]
elif sys.platform == "darwin":
    CANDIDATES = [Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")]
else:
    CANDIDATES = [Path("/usr/bin/soffice"), Path("/usr/local/bin/soffice"), Path("/opt/libreoffice/program/soffice")]

INSTALL_HINT = (
    "Zainstaluj LibreOffice (https://www.libreoffice.org, na Windows także: "
    "winget install TheDocumentFoundation.LibreOffice) albo ustaw zmienną środowiskową "
    f"{ENV_VAR} na pełną ścieżkę do soffice."
)


def find_soffice() -> Path:
    """Zwraca ścieżkę do programu soffice albo zgłasza MissingDependencyError."""
    custom = os.environ.get(ENV_VAR)
    if custom is not None:  # jawna konfiguracja ma pierwszeństwo – nie zgadujemy dalej
        path = Path(custom)
        if path.is_file():
            return path
        raise MissingDependencyError(
            f"Zmienna {ENV_VAR} wskazuje na nieistniejący plik: {custom}", INSTALL_HINT
        )

    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return Path(found)
    for path in CANDIDATES:
        if path.is_file():
            return path
    raise MissingDependencyError("Nie znaleziono programu LibreOffice.", INSTALL_HINT)


def build_command(soffice: Path, source: Path, target_format: str, outdir: Path, profile: Path) -> list[str]:
    """Polecenie jako LISTA argumentów – bez shell=True, więc spacje i znaki
    w nazwach plików nie są interpretowane przez powłokę."""
    return [
        str(soffice),
        # osobny profil: konwersja działa nawet wtedy, gdy LibreOffice jest otwarty w tle
        f"-env:UserInstallation={profile.resolve().as_uri()}",
        "--headless",
        "--norestore",
        "--convert-to", target_format,
        "--outdir", str(outdir),
        str(source.resolve()),
    ]


# DOCX i ODT to archiwa ZIP – sprawdzamy, czy w środku jest główny plik treści.
REQUIRED_ENTRY = {"docx": "word/document.xml", "odt": "content.xml"}


def check_document(source: Path) -> None:
    """Wstępna kontrola pliku. LibreOffice potrafi „przekonwertować” nawet zwykły tekst
    z rozszerzeniem .docx, więc uszkodzone pliki odrzucamy sami, przed uruchomieniem."""
    ext = source.suffix.lower().lstrip(".")
    entry = REQUIRED_ENTRY.get(ext)
    if entry is None:
        return
    try:
        with zipfile.ZipFile(source) as archive:
            ok = entry in archive.namelist()
    except zipfile.BadZipFile:
        ok = False
    if not ok:
        raise InvalidInputError(
            f"Plik {source.name} nie jest poprawnym dokumentem {ext.upper()} albo jest uszkodzony.",
            f"Otwórz go w edytorze tekstu i zapisz ponownie jako .{ext}.",
        )


def convert_with_libreoffice(source: Path, target: Path, target_format: str) -> None:
    check_document(source)
    soffice = find_soffice()

    with tempfile.TemporaryDirectory(prefix="konwerter_") as tmp:
        tmp_dir = Path(tmp)
        outdir = tmp_dir / "wynik"
        outdir.mkdir()
        command = build_command(soffice, source, target_format, outdir, PROFILE_DIR)

        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=TIMEOUT_S)
        except FileNotFoundError as exc:
            raise MissingDependencyError(f"Nie można uruchomić: {soffice}", INSTALL_HINT) from exc
        except subprocess.TimeoutExpired as exc:
            raise ConversionError(
                f"LibreOffice nie zakończył konwersji w ciągu {TIMEOUT_S} s.",
                "Plik może być bardzo duży lub uszkodzony. Zamknij LibreOffice i spróbuj ponownie.",
            ) from exc

        if result.returncode != 0:
            details = (result.stderr or result.stdout).strip() or f"kod zakończenia {result.returncode}"
            raise ConversionError(f"LibreOffice zgłosił błąd: {details}", "Sprawdź, czy plik otwiera się w LibreOffice.")

        produced = outdir / f"{source.stem}.{target_format}"
        if not produced.is_file():
            # LibreOffice często kończy się kodem 0 nawet dla uszkodzonego pliku – dlatego to sprawdzamy
            raise InvalidInputError(
                f"LibreOffice nie utworzył pliku wynikowego z {source.name}.",
                "Plik jest prawdopodobnie uszkodzony albo ma rozszerzenie niezgodne z zawartością.",
            )
        shutil.move(str(produced), str(target))


# Rejestracja kierunków – jedna funkcja obsługuje wszystkie pary przez LibreOffice.
def _register(source: str, target: str) -> None:
    @converter(source, target)
    def _convert(src: Path, dst: Path) -> None:
        convert_with_libreoffice(src, dst, target)

    _convert.__name__ = f"{source}_to_{target}"


for _src, _dst in [("docx", "pdf"), ("odt", "pdf"), ("docx", "odt"), ("odt", "docx")]:
    _register(_src, _dst)
