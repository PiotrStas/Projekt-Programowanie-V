# Uniwersalny konwerter plików

**Projekt 1 – Programowanie V**, Politechnika Opolska, Wydział Informatyki
**Autor:** Piotr Staś (nr albumu 105534)

Aplikacja desktopowa w Pythonie (Tkinter/ttk), która pozwala wybrać plik wejściowy, pokazuje
**tylko dostępne dla niego formaty docelowe**, wykonuje konwersję i zapisuje wynik we wskazanym
katalogu. Obsługuje **8 kierunków konwersji z 3 grup**: dane strukturalne, tekst/dokumenty
oraz formaty biurowe/PDF. Można z niej korzystać przez okno programu albo z wiersza poleceń.

---

## Spis treści

1. [Wymagania](#wymagania)
2. [Instalacja](#instalacja)
3. [Uruchomienie](#uruchomienie)
4. [Obsługiwane konwersje](#obsługiwane-konwersje)
5. [Zasady konwersji](#zasady-konwersji)
6. [Obsługa błędów](#obsługa-błędów)
7. [Architektura](#architektura)
8. [Dane testowe](#dane-testowe)
9. [Testy](#testy)
10. [Znane ograniczenia](#znane-ograniczenia)
11. [Rozwiązywanie problemów](#rozwiązywanie-problemów)
12. [Źródła, biblioteki i narzędzia AI](#źródła-biblioteki-i-narzędzia-ai)
13. [Historia zmian](#historia-zmian)

---

## Wymagania

| Składnik | Wersja | Do czego |
|---|---|---|
| Python | 3.10 lub nowszy | cała aplikacja (Tkinter jest w standardowej instalacji Pythona na Windows) |
| `python-docx` | 1.1 lub nowszy | konwersje TXT ↔ DOCX |
| `pytest` | 7.0 lub nowszy | testy automatyczne |
| **LibreOffice** | dowolna aktualna | konwersje DOCX/ODT → PDF oraz DOCX ↔ ODT |

Biblioteki Pythona są w pliku [`projekt-konwerter/requirements.txt`](projekt-konwerter/requirements.txt).
LibreOffice to program zewnętrzny. Bez niego działają wszystkie konwersje poza grupą C.

> Linux: Tkinter instaluje się osobno, np. `sudo apt install python3-tk`.

---

## Instalacja

### 1. Pobranie projektu

```bash
git clone <adres-tego-repozytorium>
cd Projekt-Programowanie-V/projekt-konwerter
```

Albo na GitHubie: **Code → Download ZIP**, rozpakuj i wejdź do folderu `projekt-konwerter`.

> **Wszystkie polecenia poniżej wykonuj w folderze `projekt-konwerter`.**

### 2. Biblioteki Pythona

```bash
python -m pip install -r requirements.txt
```

### 3. LibreOffice

Pobierz z https://www.libreoffice.org (instalacja typowa) albo na Windows:

```powershell
winget install TheDocumentFoundation.LibreOffice
```

Sprawdzenie instalacji (PowerShell):

```powershell
& "C:\Program Files\LibreOffice\program\soffice.exe" --version
```

Program szuka LibreOffice w tej kolejności:

1. zmienna środowiskowa `KONWERTER_SOFFICE` (pełna ścieżka do `soffice` / `soffice.exe`),
2. polecenia `soffice` / `libreoffice` w `PATH`,
3. typowe lokalizacje: `C:\Program Files\LibreOffice\program\soffice.exe` (Windows),
   `/Applications/LibreOffice.app/Contents/MacOS/soffice` (macOS), `/usr/bin/soffice` (Linux).

### 4. Sprawdzenie, czy wszystko działa

```bash
python -m pytest
python -m konwerter --lista
```

Oczekiwany wynik: `79 passed` oraz lista 8 par formatów.

---

## Uruchomienie

### Okno programu (GUI)

```bash
python -m konwerter
```

1. **Plik wejściowy → „Wybierz…”**: okno wyboru pokazuje tylko obsługiwane typy plików.
2. **Katalog zapisu** ustawia się automatycznie na folder wybranego pliku. Można go zmienić przyciskiem „Wybierz…”.
3. **Format docelowy**: lista zawiera **tylko formaty dozwolone** dla wybranego pliku i nie da się
   wpisać innej wartości. Jeśli plik ma jeden możliwy format, zostaje on wybrany automatycznie.
4. Pod listą widać **nazwę pliku wynikowego** i ostrzeżenie, jeśli taki plik już istnieje.
5. **„Konwertuj”**: konwersja działa w tle (okno się nie zawiesza, kręci się pasek postępu,
   formularz jest zablokowany). Gdy plik wynikowy istnieje, program pyta:
   - **Tak**: nadpisz,
   - **Nie**: zapisz pod nową nazwą, np. `sprawozdanie (1).pdf`,
   - **Anuluj**: przerwij.
6. Po sukcesie na dole pojawia się zielony komunikat z nazwą pliku i czasem konwersji, a przycisk
   **„Otwórz katalog”** pokazuje wynik w Eksploratorze.
7. Błędy wyświetlane są w okienku z **przyczyną** i podpowiedzią **„Co zrobić”**. Program działa dalej.

Przycisk „Konwertuj” jest aktywny tylko wtedy, gdy wybrano plik, katalog i dozwolony format.

### Wiersz poleceń (CLI)

```bash
python -m konwerter --lista                                         # wspierane pary formatów
python -m konwerter dane_testowe/sprawozdanie.docx                  # formaty dostępne dla pliku
python -m konwerter <plik> --na <format> --do <katalog> [--nadpisz]
```

Przykłady:

```bash
python -m konwerter dane_testowe/studenci.csv --na json --do wyniki
python -m konwerter dane_testowe/produkty.json --na csv --do wyniki
python -m konwerter dane_testowe/notatka.txt --na docx --do wyniki
python -m konwerter dane_testowe/sprawozdanie.docx --na txt --do wyniki
python -m konwerter dane_testowe/sprawozdanie.docx --na pdf --do wyniki
python -m konwerter dane_testowe/sprawozdanie.odt --na pdf --do wyniki
python -m konwerter dane_testowe/sprawozdanie.docx --na odt --do wyniki
python -m konwerter dane_testowe/sprawozdanie.odt --na docx --do wyniki --nadpisz
```

- Jeśli katalog z `--do` nie istnieje, zostanie utworzony.
- Bez `--nadpisz` istniejący plik **nigdy nie jest nadpisywany**. Wynik dostaje nazwę `nazwa (1).ext`, `nazwa (2).ext` itd.
- Kod wyjścia: `0` oznacza sukces, `1` błąd konwersji, `2` niepełne polecenie.

---

## Obsługiwane konwersje

| Grupa | Z | Na | Narzędzie | Znane ograniczenia |
|---|---|---|---|---|
| A – dane strukturalne | CSV | JSON | `csv`, `json` (biblioteka standardowa) | wszystkie wartości trafiają do JSON jako tekst |
| A – dane strukturalne | JSON | CSV | `csv`, `json` (biblioteka standardowa) | tylko płaska tablica obiektów, bez zagnieżdżeń |
| B – tekst i dokumenty | TXT | DOCX | `python-docx` | tylko UTF-8; domyślna czcionka, bez stylów |
| B – tekst i dokumenty | DOCX | TXT | `python-docx` | tracone formatowanie, obrazy, przypisy, nagłówki i stopki stron |
| C – formaty biurowe | DOCX | PDF | LibreOffice (headless) | układ może nieznacznie różnić się od Worda (czcionki zastępcze) |
| C – formaty biurowe | ODT | PDF | LibreOffice (headless) | jw. |
| C – formaty biurowe | DOCX | ODT | LibreOffice (headless) | złożone formatowanie i makra mogą nie zostać przeniesione |
| C – formaty biurowe | ODT | DOCX | LibreOffice (headless) | jw. |

Każda inna para jest **nieobsługiwana**: w oknie programu nie da się jej wybrać, a w CLI kończy się
komunikatem z listą dostępnych formatów.

---

## Zasady konwersji

### CSV → JSON

- Kodowanie **UTF-8** (z BOM lub bez). Inne kodowania kończą się komunikatem z instrukcją, jak zapisać plik w UTF-8.
- **Pierwszy wiersz to nagłówek**, a nazwy kolumn muszą być niepuste i unikalne.
- Separator jest **wykrywany automatycznie** z nagłówka: `,`, `;` lub tabulator (wybierany jest najczęstszy).
- Pola w cudzysłowach mogą zawierać separator, cudzysłów (`""`) i znaki nowej linii.
- Puste linie są pomijane, a każdy wiersz musi mieć tyle pól, co nagłówek.
- **Wartości nie są zgadywane**: `012345` zostaje `"012345"`, `4,50` zostaje `"4,50"`, a pusta komórka daje `""`.
- **Kolejność i nazwy kolumn są zachowane.**
- Wynikowy JSON: UTF-8, polskie znaki zapisane wprost (nie jako `\uXXXX`), wcięcie 2 spacje.

### JSON → CSV

Akceptowana struktura to **tablica obiektów**, gdzie każdy obiekt to jeden wiersz CSV:

```json
[
  {"id": 1, "nazwa": "Długopis", "cena": 4.99, "dostępny": true, "uwagi": null},
  {"id": 2, "nazwa": "Zeszyt"}
]
```

- Wartości mogą być tekstem, liczbą, `true`/`false` albo `null`. Zagnieżdżone obiekty i listy kończą się błędem z opisem, które pole jest problemem.
- Kolumny to wszystkie klucze w **kolejności pierwszego wystąpienia**. Brakujące pole daje pustą komórkę.
- `null` daje pustą komórkę, a `true`/`false` daje tekst `true`/`false`.
- Wynikowy CSV: **UTF-8 z BOM** (Excel poprawnie pokazuje polskie znaki), separator `,`.

### TXT → DOCX

- Plik TXT w UTF-8.
- **Każda linia tekstu to jeden akapit**, a pusta linia to pusty akapit. Tabulatory są zachowane.
- Znaki sterujące niedozwolone w XML (np. `\x00`) są usuwane.

### DOCX → TXT

- Tekst akapitów i tabel w **kolejności z dokumentu**.
- Komórki tabeli rozdzielone są tabulatorem, a każdy wiersz tabeli zajmuje osobną linię.
- Wynik w UTF-8. Konwersja TXT → DOCX → TXT jest bezstratna.

### DOCX/ODT → PDF, DOCX ↔ ODT (LibreOffice)

- LibreOffice uruchamiany jest przez `subprocess.run` z **listą argumentów, bez `shell=True`**, z limitem czasu 120 s.
- Sprawdzany jest **kod zakończenia** oraz to, czy plik wynikowy **faktycznie powstał**.
- Przed uruchomieniem program sprawdza, czy DOCX/ODT jest poprawnym dokumentem, bo LibreOffice
  „przekonwertowałby” nawet zwykły tekst z rozszerzeniem `.docx`.
- Wynik powstaje najpierw w katalogu tymczasowym (LibreOffice sam nadpisałby istniejący plik bez
  pytania), a dopiero potem trafia do katalogu docelowego zgodnie z polityką nadpisywania.
- Konwersja używa osobnego profilu LibreOffice, więc działa także przy otwartym LibreOffice.
  Pierwsza konwersja trwa przez to kilka sekund dłużej.

### Wspólne dla wszystkich konwersji

Wynik zapisywany jest najpierw do pliku `*.part`. Docelowa nazwa pojawia się dopiero po sukcesie,
więc **po błędzie nie zostaje uszkodzony ani niepełny plik**.

---

## Obsługa błędów

Każdy błąd ma **przyczynę** i **podpowiedź, co zrobić**. Błędy nie zamykają programu i są zapisywane
do pliku `konwerter.log` w folderze projektu.

| Sytuacja | Reakcja programu |
|---|---|
| plik nie istnieje (np. usunięty po wybraniu) | „Nie znaleziono pliku wejściowego” |
| nieobsługiwany typ pliku lub para formatów | w GUI opcja niedostępna, w CLI lista dostępnych formatów |
| plik w kodowaniu innym niż UTF-8 | informacja o kodowaniu i instrukcja zapisu w UTF-8 |
| błędny JSON | „Niepoprawny JSON … (wiersz X, kolumna Y)” |
| JSON z zagnieżdżeniami / zła struktura | wskazanie elementu i pola |
| CSV ze złą liczbą pól / pustym lub powtórzonym nagłówkiem | numer wiersza lub nazwa kolumny |
| uszkodzony DOCX/ODT | „nie jest poprawnym dokumentem … albo jest uszkodzony” |
| brak `python-docx` | „Brak biblioteki python-docx” i polecenie instalacji |
| brak LibreOffice | komunikat z instrukcją instalacji; pozostałe konwersje działają |
| LibreOffice zwrócił błąd / przekroczył czas / nie utworzył pliku | komunikat z treścią błędu |
| plik docelowy istnieje | GUI: pytanie Tak/Nie/Anuluj; CLI: bezpieczna nazwa `nazwa (1)` |
| brak katalogu lub uprawnień do zapisu, plik otwarty w innym programie | komunikat z podpowiedzią |

---

## Architektura

Logika konwersji jest **całkowicie oddzielona od GUI**. Konwertery rejestrują się w rejestrze,
a okno i CLI tylko z niego korzystają.

```
          GUI (gui.py)        CLI (cli.py)
                 \               /
                  v             v
     core.py:  available_targets()  ConversionRequest.validate()  execute()
                                |
                          REGISTRY[(z, na)]
                 /              |               \
     structured.py          text.py           office.py
     CSV <-> JSON         TXT <-> DOCX     LibreOffice (PDF, ODT, DOCX)
```

- **`core.py`**: rejestr `REGISTRY`, dekorator `@converter`, `ConversionRequest` z walidacją,
  `available_targets()`, `execute()` (polityka nadpisywania, zapis przez `*.part`, logowanie, czas).
- **`errors.py`**: wspólny model błędów: `ConversionError` z polami `message` i `hint`.
  Klasy pochodne to `InvalidInputError`, `UnsupportedConversionError`, `OutputError` i `MissingDependencyError`.
- **`gui.py`**: okno Tkinter/ttk. Konwersja działa w **wątku roboczym**, który przekazuje wynik przez kolejkę.
  Okno odczytuje ją co 100 ms przez `root.after()`, bo Tkintera wolno zmieniać tylko z głównego wątku.

**Dodanie nowej pary formatów** wymaga tylko jednej funkcji w `konwerter/converters/`:

```python
@converter("txt", "pdf")
def txt_to_pdf(source: Path, target: Path) -> None:
    ...
```

Nowy format sam pojawi się w oknie, w CLI i w `--lista`. Rdzenia ani interfejsu nie trzeba zmieniać.

### Struktura repozytorium

```
Projekt-Programowanie-V/
├── README.md                     ten plik
└── projekt-konwerter/
    ├── requirements.txt          zależności Pythona
    ├── CHANGELOG.md              dziennik zmian (Lab 2–5)
    ├── .gitignore
    ├── konwerter/
    │   ├── __main__.py           python -m konwerter
    │   ├── cli.py                wiersz poleceń; bez argumentów uruchamia okno
    │   ├── gui.py                okno Tkinter/ttk (bez logiki konwersji)
    │   ├── core.py               rejestr, walidacja, execute()
    │   ├── errors.py             model błędów
    │   └── converters/
    │       ├── common.py         wspólny odczyt UTF-8
    │       ├── structured.py     Grupa A: CSV <-> JSON
    │       ├── text.py           Grupa B: TXT <-> DOCX
    │       └── office.py         Grupa C: LibreOffice
    ├── tests/                    testy pytest
    └── dane_testowe/             przykładowe pliki wejściowe
```

---

## Dane testowe

Pliki w folderze [`projekt-konwerter/dane_testowe/`](projekt-konwerter/dane_testowe/):

| Plik | Co sprawdza | Oczekiwany wynik |
|---|---|---|
| `studenci.csv` | separator `;`, polskie znaki, puste wartości, `;` i `"` w cudzysłowie, zera wiodące | JSON z 3 obiektami, dane bez zmian |
| `produkty.json` | liczby, `true/false`, `null`, różne zestawy kluczy, przecinek w tekście | CSV z 5 kolumnami, brakujące pola puste |
| `bledny.json` | przecinek przed `}` | „Niepoprawny JSON … (wiersz 3, …)”, brak pliku wynikowego |
| `zagniezdzony.json` | obiekt w obiekcie | komunikat o nieobsługiwanym zagnieżdżeniu |
| `zla_liczba_kolumn.csv` | wiersz z nadmiarowym polem | „Wiersz 3: 4 pól, a nagłówek ma 3 kolumn” |
| `notatka.txt` | polskie znaki, puste linie, tabulatory | DOCX z akapitem na każdą linię |
| `sprawozdanie.docx` | nagłówek, pogrubienie, tabela, polskie znaki | TXT z tabelą rozdzieloną tabulatorami; poprawny PDF i ODT |
| `sprawozdanie.odt` | ten sam dokument w formacie ODT | poprawny PDF i DOCX |
| `uszkodzony.docx` | zwykły tekst z rozszerzeniem `.docx` | „nie jest poprawnym dokumentem DOCX albo jest uszkodzony” |
| `moj.docx` | dokument z Worda: nagłówek, lista, tabela, polskie znaki | poprawny PDF, TXT i ODT |
| `moj.odt` | dokument z LibreOffice Writer: nagłówek, lista numerowana | poprawny PDF i DOCX |
| `moj.txt` | tekst z Notatnika (UTF-8) z pustymi liniami i tabulatorami | DOCX z akapitem na każdą linię |

**Brak LibreOffice** można sprawdzić bez odinstalowywania, przez zmianę konfiguracji (PowerShell):

```powershell
$env:KONWERTER_SOFFICE = "C:\nie_ma\soffice.exe"
python -m konwerter dane_testowe/sprawozdanie.docx --na pdf --do wyniki
Remove-Item Env:KONWERTER_SOFFICE
```

---

## Testy

```bash
python -m pytest -v
```

Wynik: **79 testów, wszystkie zaliczone** (Windows, Python 3.13, LibreOffice zainstalowany).

| Plik | Zakres |
|---|---|
| `test_core.py` | `validate()`, `available_targets()`, polityka nadpisywania, bezpieczne nazwy, brak plików `.part` po błędzie |
| `test_structured.py` | CSV ↔ JSON: polskie znaki, puste wartości, BOM, pola wieloliniowe, separatory, błędne i uszkodzone dane, konwersja w obie strony |
| `test_text.py` | TXT ↔ DOCX: akapity, puste linie, tabulatory, tabele, znaki sterujące, złe kodowanie, uszkodzony DOCX, konwersja w obie strony |
| `test_office.py` | wykrywanie LibreOffice (także jego brak), polecenie bez powłoki, kod zakończenia, limit czasu, brak pliku wynikowego, prawdziwe konwersje DOCX/ODT → PDF/ODT/DOCX |
| `test_gui.py` | logika okna (formaty, podgląd nazwy, aktywność przycisku) oraz prawdziwe okno: konwersja w tle, nadpisanie Tak/Nie/Anuluj, błędy, plik usunięty po wybraniu |

- Testy wymagające LibreOffice są pomijane (`SKIPPED`), gdy go nie ma.
- Testy okna są pomijane na komputerze bez ekranu.
- Okienka dialogowe są w testach podstawiane (`monkeypatch`), więc testy nie czekają na kliknięcie.

### Minimalna macierz testów z instrukcji

| Przypadek | Oczekiwany rezultat | Wynik |
|---|---|---|
| poprawny plik w każdej grupie | otwieralny plik o właściwej treści | ✅ testy automatyczne i ręczne (wszystkie 8 par) |
| błędny lub uszkodzony plik | brak awarii, jednoznaczny komunikat | ✅ `bledny.json`, `zagniezdzony.json`, `zla_liczba_kolumn.csv`, `uszkodzony.docx` |
| nieobsługiwana para | opcja niewidoczna lub zablokowana | ✅ GUI pokazuje tylko dozwolone formaty; CLI zwraca błąd |
| brak LibreOffice / biblioteki | kontrolowany błąd z instrukcją | ✅ zmienna `KONWERTER_SOFFICE`; komunikat o braku `python-docx` |
| plik docelowy już istnieje | pytanie o nadpisanie albo bezpieczna nazwa | ✅ GUI: Tak/Nie/Anuluj; CLI: `nazwa (1)` |
| polskie znaki i puste wartości | dane i struktura poprawne | ✅ porównanie wejścia i wyjścia w testach w obie strony |

---

## Znane ograniczenia

- Nie jest obsługiwany stary format `.doc`, pliki chronione hasłem ani pliki z makrami.
- Konwersje nie zachowują złożonego formatowania, osadzonych wykresów, przypisów ani identycznego układu stron.
- CSV → JSON nie rozpoznaje typów danych: wszystkie wartości są tekstem.
- JSON → CSV obsługuje tylko płaską tablicę obiektów.
- Wynikowy CSV używa przecinka jako separatora. Polska wersja Excela może przy otwieraniu pokazać dane w jednej
  kolumnie. Wtedy użyj **Dane → Z pliku tekstowego/CSV** i wybierz przecinek.
- Konwersje biurowe wymagają zainstalowanego LibreOffice. Układ PDF może się minimalnie różnić od Worda.
- Program wykonuje jedną konwersję naraz.

---

## Rozwiązywanie problemów

| Problem | Rozwiązanie |
|---|---|
| `python` nie jest rozpoznawany | zainstaluj Pythona z python.org z opcją **Add Python to PATH** albo użyj `py` zamiast `python` |
| `No module named 'docx'` | `python -m pip install -r requirements.txt` |
| `No module named konwerter` | uruchamiaj polecenia w folderze `projekt-konwerter`, nie w głównym folderze repozytorium |
| „Nie znaleziono programu LibreOffice” | zainstaluj LibreOffice albo ustaw `KONWERTER_SOFFICE` na pełną ścieżkę do `soffice.exe` |
| pierwsza konwersja do PDF trwa długo | to normalne: LibreOffice tworzy profil przy pierwszym uruchomieniu |
| „Nie udało się zapisać wyniku” | zamknij plik wynikowy w Wordzie lub innym programie i spróbuj ponownie |

---

## Źródła, biblioteki i narzędzia AI

**Dokumentacja:**

- [Python – `tkinter.filedialog`](https://docs.python.org/3/library/dialog.html), [`tkinter.ttk`](https://docs.python.org/3/library/tkinter.ttk.html)
- [Python – `csv`](https://docs.python.org/3/library/csv.html), [`json`](https://docs.python.org/3/library/json.html), [`pathlib`](https://docs.python.org/3/library/pathlib.html)
- [Python – `subprocess`](https://docs.python.org/3/library/subprocess.html), [`threading`](https://docs.python.org/3/library/threading.html)
- [python-docx](https://python-docx.readthedocs.io/)
- [LibreOffice – parametry wiersza poleceń](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html)
- [pytest](https://docs.pytest.org/)

**Biblioteki i narzędzia:**

- `python-docx` (MIT)
- `pytest` (MIT)
- LibreOffice (MPL 2.0)
- biblioteka standardowa Pythona

**Inne:**

- Szkielet rejestru konwerterów jest oparty na kodzie inspiracyjnym z instrukcji projektu.
- Narzędzia AI: Claude (Anthropic) – pomoc przy kodzie i dokumentacji.

---

## Historia zmian

Postęp prac w kolejnych laboratoriach opisuje [`projekt-konwerter/CHANGELOG.md`](projekt-konwerter/CHANGELOG.md).
Szczegółowa historia jest w commitach repozytorium Git.
