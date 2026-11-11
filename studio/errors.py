"""Wspólny model błędów aplikacji.

Każdy błąd ma:
- message – co się stało (przyczyna),
- hint    – co użytkownik może zrobić (dalszy krok).
"""


class StudioError(Exception):
    """Bazowy, kontrolowany błąd aplikacji."""

    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint

    def __str__(self) -> str:
        return f"{self.message}\nCo zrobić: {self.hint}" if self.hint else self.message


class DataLoadError(StudioError):
    """Nie da się wczytać pliku: brak pliku, złe kodowanie, wadliwy wiersz, pusty plik."""


class ColumnError(StudioError):
    """Brak kolumny albo kolumna ma zły typ dla danej operacji."""


class ParameterError(StudioError):
    """Niepoprawne parametry operacji lub reguły (np. min > max, nieznana strategia)."""


class ExportError(StudioError):
    """Nie da się zapisać pliku wynikowego."""
