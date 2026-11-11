# Dziennik zmian

## Lab 2
- Rejestr konwerterów (`@converter`), `ConversionRequest.validate()`, `available_targets()`, `execute()`.
- Wspólny model błędów z przyczyną i podpowiedzią; logowanie do `konwerter.log`.
- Bezpieczna polityka nadpisywania (`nazwa (1).ext`) i zapis przez plik tymczasowy `.part`.
- Konwertery CSV → JSON i JSON → CSV z opisaną semantyką.
- Uruchamianie z wiersza poleceń (`python -m konwerter`).
- Dane testowe i testy pytest.

## Lab 3
- Grupa B: TXT → DOCX i DOCX → TXT (python-docx); akapity i tabele w kolejności z dokumentu.
- Grupa C: DOCX → PDF, ODT → PDF, DOCX → ODT, ODT → DOCX przez LibreOffice w trybie headless.
- Wykrywanie LibreOffice (zmienna KONWERTER_SOFFICE, PATH, typowe ścieżki Windows/macOS/Linux).
- Wywołanie bez shell=True, limit czasu, kontrola kodu zakończenia i istnienia pliku wynikowego.
- Wstępna kontrola poprawności plików DOCX/ODT; wspólny odczyt UTF-8 w converters/common.py.
- Nowe dane testowe i testy (56 testów).

## Lab 4
- Okno programu w Tkinter/ttk (`konwerter/gui.py`), uruchamiane przez `python -m konwerter` bez argumentów.
- Wybór pliku i katalogu w oknach systemowych; filtry typów plików budowane z rejestru konwerterów.
- Lista formatów zależna od pliku (tylko dozwolone pary, bez możliwości wpisania własnej wartości).
- Podgląd nazwy wyniku z ostrzeżeniem, gdy plik już istnieje; pytanie Tak/Nie/Anuluj o nadpisanie.
- Konwersja w wątku roboczym (kolejka + `root.after`), pasek postępu, blokada formularza w trakcie pracy.
- Komunikaty sukcesu w pasku statusu, błędy w okienku z przyczyną i podpowiedzią; przycisk „Otwórz katalog”.
- Testy logiki GUI i okna (79 testów; testy okna pomijane bez ekranu).
