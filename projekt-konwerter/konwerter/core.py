"""Rdzeń aplikacji: rejestr konwerterów, walidacja żądania i uruchamianie konwersji.

Ten moduł NIE wie nic o GUI ani o konkretnych formatach. Konwertery rejestrują się
same dekoratorem @converter, więc dodanie nowej pary formatów nie wymaga zmian tutaj
ani w interfejsie (GUI pobierze listę z available_targets()).
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .errors import ConversionError, InvalidInputError, OutputError, UnsupportedConversionError

log = logging.getLogger(__name__)

# Konwerter dostaje (plik_wejściowy, plik_wyjściowy) i zapisuje wynik pod wskazaną ścieżką.
# O nazwie pliku wynikowego (i nadpisywaniu) decyduje execute(), a nie konwerter.
Converter = Callable[[Path, Path], None]
REGISTRY: dict[tuple[str, str], Converter] = {}


def normalize(fmt: str) -> str:
    """'.CSV' -> 'csv'. Formaty w rejestrze trzymamy bez kropki, małymi literami."""
    return fmt.strip().lower().lstrip(".")


def converter(source: str, target: str) -> Callable[[Converter], Converter]:
    """Dekorator rejestrujący pojedynczy kierunek konwersji."""

    def register(func: Converter) -> Converter:
        key = (normalize(source), normalize(target))
        if key in REGISTRY:
            raise ValueError(f"Kierunek {key[0]} -> {key[1]} jest już zarejestrowany")
        REGISTRY[key] = func
        return func

    return register


def available_targets(source: Path) -> list[str]:
    """Formaty docelowe dostępne dla danego pliku (na podstawie rozszerzenia)."""
    ext = normalize(source.suffix)
    return sorted(target for (src, target) in REGISTRY if src == ext)


def supported_pairs() -> list[tuple[str, str]]:
    """Pełna macierz wspieranych par – do README, CLI i GUI."""
    return sorted(REGISTRY)


@dataclass(frozen=True)
class ConversionRequest:
    source: Path
    target_format: str
    output_dir: Path
    overwrite: bool = False

    @property
    def key(self) -> tuple[str, str]:
        return normalize(self.source.suffix), normalize(self.target_format)

    def validate(self) -> None:
        """Sprawdza wszystko, co da się sprawdzić PRZED konwersją."""
        if not str(self.source).strip() or self.source == Path():
            raise InvalidInputError("Nie wybrano pliku wejściowego.", "Wskaż plik do konwersji.")
        if not self.source.is_file():
            raise InvalidInputError(
                f"Nie znaleziono pliku wejściowego: {self.source}",
                "Sprawdź, czy ścieżka jest poprawna i czy plik nie został przeniesiony.",
            )
        if not self.target_format.strip():
            raise UnsupportedConversionError(
                "Nie wybrano formatu docelowego.", "Wybierz format z listy dostępnych."
            )
        if self.key not in REGISTRY:
            src, dst = self.key
            dostepne = ", ".join(available_targets(self.source)) or "brak"
            raise UnsupportedConversionError(
                f"Nieobsługiwana konwersja: {src or '(brak rozszerzenia)'} -> {dst}",
                f"Dla tego pliku dostępne są formaty: {dostepne}.",
            )
        if not self.output_dir.is_dir():
            raise OutputError(
                f"Nie znaleziono katalogu docelowego: {self.output_dir}",
                "Wybierz istniejący katalog albo go utwórz.",
            )
        if not os.access(self.output_dir, os.W_OK):
            raise OutputError(
                f"Brak uprawnień do zapisu w katalogu: {self.output_dir}",
                "Wybierz inny katalog (np. Dokumenty).",
            )

    def planned_output(self) -> Path:
        """Ścieżka, pod którą trafi wynik, jeśli nie ma konfliktu nazw."""
        return self.output_dir / f"{self.source.stem}.{normalize(self.target_format)}"


def safe_path(path: Path) -> Path:
    """Zwraca wolną nazwę: raport.json -> raport (1).json -> raport (2).json ..."""
    if not path.exists():
        return path
    n = 1
    while True:
        candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def execute(request: ConversionRequest) -> Path:
    """Waliduje żądanie, uruchamia konwerter i zwraca ścieżkę pliku wynikowego.

    Polityka nadpisywania: bez overwrite=True istniejący plik NIGDY nie jest
    nadpisywany – wynik dostaje bezpieczną nazwę z numerem. (GUI z Lab 4 zapyta
    użytkownika i przekaże jego decyzję w polu overwrite.)

    Wynik zapisujemy najpierw do pliku tymczasowego *.part i dopiero po sukcesie
    zmieniamy mu nazwę – po błędzie nie zostaje uszkodzony plik wynikowy.
    """
    request.validate()
    func = REGISTRY[request.key]

    target = request.planned_output()
    if not request.overwrite:
        target = safe_path(target)
    tmp = target.with_name(target.name + ".part")

    start = time.perf_counter()
    log.info("Start: %s -> %s", request.source, target)
    try:
        func(request.source, tmp)
        os.replace(tmp, target)
    except ConversionError:
        log.warning("Konwersja nieudana: %s", request.source, exc_info=True)
        raise
    except OSError as exc:
        log.exception("Błąd systemu plików")
        raise OutputError(
            f"Nie udało się zapisać wyniku: {exc.strerror or exc}",
            "Sprawdź, czy plik nie jest otwarty w innym programie i czy jest miejsce na dysku.",
        ) from exc
    except Exception as exc:  # ostatnia linia obrony – aplikacja nie może się wysypać
        log.exception("Nieoczekiwany błąd konwertera")
        raise ConversionError(
            f"Nieoczekiwany błąd podczas konwersji: {exc}",
            "Szczegóły zapisano w pliku konwerter.log.",
        ) from exc
    finally:
        if tmp.exists():
            tmp.unlink()

    log.info("Gotowe w %.3f s: %s", time.perf_counter() - start, target)
    return target
