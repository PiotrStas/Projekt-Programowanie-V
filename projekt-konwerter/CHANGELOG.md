# Dziennik zmian

## Lab 2
- Rejestr konwerterów (`@converter`), `ConversionRequest.validate()`, `available_targets()`, `execute()`.
- Wspólny model błędów z przyczyną i podpowiedzią; logowanie do `konwerter.log`.
- Bezpieczna polityka nadpisywania (`nazwa (1).ext`) i zapis przez plik tymczasowy `.part`.
- Konwertery CSV → JSON i JSON → CSV z opisaną semantyką.
- Uruchamianie z wiersza poleceń (`python -m konwerter`).
- Dane testowe i testy pytest.
