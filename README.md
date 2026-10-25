# Uniwersalny konwerter plików

Projekt 1 – Programowanie V, Politechnika Opolska.
Autor: Piotr Staś (nr albumu 105534)

Aplikacja konwertuje pliki między formatami. Logika konwersji jest oddzielona od interfejsu:
konwertery rejestrują się w rejestrze (`konwerter/core.py`), a interfejs pobiera z niego listę
dostępnych formatów docelowych dla wybranego pliku.

> **Stan: Lab 3** – działa 8 kierunków konwersji z 3 grup, uruchamianych z wiersza poleceń.
> GUI (Tkinter) zostanie dodane na Lab 4.

## Wymagania

- Python 3.10 lub nowszy
- biblioteki z `requirements.txt`: `python-docx` (pliki DOCX), `pytest` (testy)
- **LibreOffice** – tylko dla Grupy C (DOCX/ODT → PDF, DOCX ↔ ODT)

```bash
python -m pip install -r requirements.txt
```

### LibreOffice

Pobierz z https://www.libreoffice.org (instalacja typowa) albo na Windows:

```
winget install TheDocumentFoundation.LibreOffice
```

Program szuka LibreOffice w tej kolejności:

1. zmienna środowiskowa `KONWERTER_SOFFICE` (pełna ścieżka do `soffice` / `soffice.exe`),
2. polecenia `soffice` / `libreoffice` w `PATH`,
3. typowe lokalizacje: `C:\Program Files\LibreOffice\program\soffice.exe` (Windows),
   `/Applications/LibreOffice.app/Contents/MacOS/soffice` (macOS), `/usr/bin/soffice` (Linux).

Gdy LibreOffice nie zostanie znaleziony, konwersje z Grupy C kończą się komunikatem z instrukcją
instalacji – pozostałe kierunki działają normalnie. Sprawdzenie instalacji:

```
& "C:\Program Files\LibreOffice\program\soffice.exe" --version      # PowerShell
```

Pierwsza konwersja przez LibreOffice trwa kilka sekund dłużej – tworzy się osobny profil programu
(w katalogu tymczasowym systemu), dzięki któremu konwersja działa także przy otwartym LibreOffice.

## Uruchomienie

Polecenia wykonuj w katalogu projektu (tam, gdzie jest ten plik).

```bash
python -m konwerter --lista                                        # macierz wspieranych par
python -m konwerter dane_testowe/sprawozdanie.docx                 # formaty dostępne dla pliku
python -m konwerter dane_testowe/studenci.csv --na json --do wyniki
python -m konwerter dane_testowe/produkty.json --na csv --do wyniki
python -m konwerter dane_testowe/notatka.txt --na docx --do wyniki
python -m konwerter dane_testowe/sprawozdanie.docx --na txt --do wyniki
python -m konwerter dane_testowe/sprawozdanie.docx --na pdf --do wyniki
python -m konwerter dane_testowe/sprawozdanie.odt --na pdf --do wyniki
python -m konwerter dane_testowe/sprawozdanie.docx --na odt --do wyniki --nadpisz
```

Jeśli katalog podany w `--do` nie istnieje, zostanie utworzony. Gdy plik wynikowy już istnieje,
program **nie nadpisuje go**, tylko zapisuje wynik jako `nazwa (1).ext`, `nazwa (2).ext` …
(chyba że podasz `--nadpisz`). Błędy są wypisywane z przyczyną i podpowiedzią („Co zrobić: …”)
oraz zapisywane do `konwerter.log`.

## Macierz wspieranych konwersji

| Grupa | Z | Na | Narzędzie | Znane ograniczenia |
|---|---|---|---|---|
| A – dane strukturalne | CSV | JSON | `csv`, `json` (wbudowane) | wszystkie wartości trafiają do JSON jako tekst |
| A – dane strukturalne | JSON | CSV | `csv`, `json` (wbudowane) | tylko płaska tablica obiektów, bez zagnieżdżeń |
| B – tekst i dokumenty | TXT | DOCX | `python-docx` | tylko UTF-8; domyślna czcionka, bez stylów |
| B – tekst i dokumenty | DOCX | TXT | `python-docx` | tracone formatowanie, obrazy, przypisy, nagłówki/stopki stron |
| C – formaty biurowe | DOCX | PDF | LibreOffice | układ może nieznacznie różnić się od Worda (czcionki zastępcze) |
| C – formaty biurowe | ODT | PDF | LibreOffice | jw. |
| C – formaty biurowe | DOCX | ODT | LibreOffice | złożone formatowanie i makra mogą nie zostać przeniesione |
| C – formaty biurowe | ODT | DOCX | LibreOffice | jw. |

Nie obsługujemy starego formatu `.doc`, plików chronionych hasłem ani zachowania identycznego układu stron.

## Semantyka konwersji

### CSV ↔ JSON

**Wejściowy CSV**

- kodowanie UTF-8 (z BOM lub bez), inne kodowania → komunikat z instrukcją,
- pierwszy wiersz to nagłówek; nazwy kolumn muszą być niepuste i unikalne,
- separator wykrywany z nagłówka: `,` `;` lub tabulator (najczęstszy z nich),
- pola w cudzysłowach mogą zawierać separator, cudzysłów (`""`) i nowe linie,
- puste linie są pomijane, każdy wiersz musi mieć tyle pól co nagłówek,
- wartości nie są zgadywane: `012345` zostaje `"012345"`, `4,50` zostaje `"4,50"`, pusta komórka → `""`.

**Akceptowany JSON**

```json
[
  {"id": 1, "nazwa": "Długopis", "cena": 4.99, "dostępny": true, "uwagi": null},
  {"id": 2, "nazwa": "Zeszyt"}
]
```

- tablica obiektów; każdy obiekt = jeden wiersz CSV,
- wartości: tekst, liczba, `true`/`false`, `null`; zagnieżdżone obiekty i listy → błąd,
- kolumny = wszystkie klucze w kolejności pierwszego wystąpienia; brakujące pole → pusta komórka.

**Wyjściowy CSV**: UTF-8 z BOM, separator `,`, `null` → pusta komórka, `true`/`false` → `true`/`false`.
**Wyjściowy JSON**: UTF-8, polskie znaki zapisane wprost (nie jako sekwencje `\uXXXX`), wcięcie 2 spacje.

### TXT ↔ DOCX

- TXT w UTF-8; **każda linia = jeden akapit**, pusta linia = pusty akapit, tabulatory zachowane,
- znaki sterujące niedozwolone w XML (np. `\x00`) są usuwane,
- DOCX → TXT: akapity i tabele w kolejności z dokumentu; komórki tabeli rozdzielone tabulatorem,
  każdy wiersz tabeli w osobnej linii; wynik w UTF-8,
- konwersja TXT → DOCX → TXT jest bezstratna.

### Formaty biurowe (LibreOffice)

- LibreOffice uruchamiany przez `subprocess.run` z listą argumentów (bez `shell=True`), z limitem czasu 120 s,
- sprawdzany jest kod zakończenia **i** to, czy plik wynikowy faktycznie powstał,
- przed uruchomieniem sprawdzamy, czy DOCX/ODT jest poprawnym archiwum z treścią dokumentu
  (LibreOffice „przekonwertowałby” nawet zwykły tekst z rozszerzeniem `.docx`),
- LibreOffice zapisuje wynik do katalogu tymczasowego (sam nadpisałby istniejący plik bez pytania),
  a dopiero potem wynik trafia do katalogu docelowego zgodnie z polityką nadpisywania.

Każdy wynik jest zapisywany najpierw do pliku `*.part`, a nazwa docelowa pojawia się dopiero
po sukcesie – po błędzie nie zostaje niepełny plik.

## Struktura projektu

```
konwerter/
  core.py               rejestr konwerterów, ConversionRequest, validate(), execute()
  errors.py             wspólny model błędów (przyczyna + podpowiedź)
  cli.py, __main__.py   uruchamianie z wiersza poleceń
  converters/
    common.py           wspólne funkcje (odczyt UTF-8)
    structured.py       Grupa A: CSV <-> JSON
    text.py             Grupa B: TXT <-> DOCX
    office.py           Grupa C: LibreOffice (wykrywanie, wywołanie, kontrola wyniku)
tests/                  testy pytest
dane_testowe/           przykładowe pliki wejściowe
```

Dodanie nowej pary formatów = funkcja z dekoratorem `@converter("z", "na")` w module
w `konwerter/converters/` – bez zmian w rdzeniu i interfejsie.

## Dane testowe

| Plik | Co sprawdza | Oczekiwany wynik |
|---|---|---|
| `studenci.csv` | separator `;`, polskie znaki, puste wartości, `;` i `"` w cudzysłowie, zera wiodące | poprawny JSON z 3 obiektami, dane bez zmian |
| `produkty.json` | liczby, `true/false`, `null`, różne zestawy kluczy, przecinek w tekście | CSV z 5 kolumnami, brakujące pola puste |
| `bledny.json` | przecinek przed `}` | komunikat „Niepoprawny JSON … (wiersz 3, kolumna …)”, brak pliku wynikowego |
| `zagniezdzony.json` | obiekt w obiekcie | komunikat o nieobsługiwanym zagnieżdżeniu |
| `zla_liczba_kolumn.csv` | wiersz z nadmiarowym polem | komunikat „Wiersz 3: 4 pól, a nagłówek ma 3 kolumn” |
| `notatka.txt` | polskie znaki, puste linie, tabulatory | DOCX z akapitem na każdą linię |
| `sprawozdanie.docx` | nagłówek, pogrubienie, tabela, polskie znaki | TXT z tabelą rozdzieloną tabulatorami; poprawny PDF/ODT |
| `sprawozdanie.odt` | ten sam dokument w formacie ODT | poprawny PDF/DOCX |
| `uszkodzony.docx` | zwykły tekst z rozszerzeniem `.docx` | komunikat „nie jest poprawnym dokumentem DOCX albo jest uszkodzony” |

**Brak LibreOffice** można sprawdzić bez odinstalowywania – przez zmianę konfiguracji:

```
$env:KONWERTER_SOFFICE = "C:\nie_ma\soffice.exe"       # PowerShell
python -m konwerter dane_testowe/sprawozdanie.docx --na pdf --do wyniki
Remove-Item Env:KONWERTER_SOFFICE                       # przywrócenie
```

## Testy

```bash
python -m pytest -v
```

Testy automatyczne obejmują: `validate()`, `available_targets()`, politykę nadpisywania, konwertery
CSV ↔ JSON i TXT ↔ DOCX (poprawne dane, polskie znaki, puste wartości, BOM, błędne i uszkodzone pliki,
konwersje „w obie strony”), wykrywanie LibreOffice (także jego brak), obsługę kodu zakończenia,
przekroczenia czasu i braku pliku wynikowego (na podstawionym `subprocess.run`) oraz prawdziwe
konwersje przez LibreOffice. Testy wymagające LibreOffice są pomijane (`SKIPPED`), gdy go nie ma.

## Wykorzystane źródła i narzędzia AI

- Dokumentacja Pythona: [`csv`](https://docs.python.org/3/library/csv.html),
  [`json`](https://docs.python.org/3/library/json.html), [`pathlib`](https://docs.python.org/3/library/pathlib.html),
  [`subprocess`](https://docs.python.org/3/library/subprocess.html)
- [python-docx](https://python-docx.readthedocs.io/)
- [LibreOffice – parametry wiersza poleceń](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html)
- Szkielet rejestru konwerterów oparty na kodzie inspiracyjnym z instrukcji projektu.
- Narzędzia AI: Claude (Anthropic) – pomoc przy kodzie i dokumentacji.

## Dziennik zmian

Zobacz [CHANGELOG.md](CHANGELOG.md) oraz historię w repozytorium Git.
