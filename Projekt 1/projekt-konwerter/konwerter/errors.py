"""Wspólny model błędów konwertera.

Każdy błąd niesie dwie informacje:
- message – CO się stało (przyczyna),
- hint    – CO użytkownik może zrobić (dalszy krok).
Dzięki temu CLI i (później) GUI pokazują komunikaty w jednolity sposób.
"""


class ConversionError(Exception):
    """Bazowy, kontrolowany błąd konwersji."""

    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint

    def __str__(self) -> str:
        if self.hint:
            return f"{self.message}\nCo zrobić: {self.hint}"
        return self.message


class InvalidInputError(ConversionError):
    """Plik wejściowy nie istnieje, jest pusty albo ma błędną treść."""


class UnsupportedConversionError(ConversionError):
    """Wybrana para formatów nie jest obsługiwana."""


class OutputError(ConversionError):
    """Nie da się zapisać wyniku (katalog, uprawnienia, konflikt nazw)."""


class MissingDependencyError(ConversionError):
    """Brakuje biblioteki lub narzędzia zewnętrznego (np. LibreOffice) – Lab 3."""
