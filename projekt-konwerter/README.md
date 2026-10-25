# Uniwersalny konwerter plików

Projekt 1 – Programowanie V, Politechnika Opolska.
Autor: Piotr Staś (nr albumu 105534)

Aplikacja konwertuje pliki między formatami. Logika konwersji jest oddzielona od interfejsu:
konwertery rejestrują się w rejestrze (`konwerter/core.py`), a interfejs pobiera z niego listę
dostępnych formatów docelowych dla wybranego pliku.

> **Stan: Lab 2** – działa CSV ↔ JSON z wiersza poleceń. GUI (Tkinter) i formaty dokumentów
> zostaną dodane na kolejnych laboratoriach.

## Wymagania

- Python 3.10 lub nowszy
- `pytest` – tylko do uruchomienia testów

```bash
pip install -r requirements.txt
```

## Uruchomienie

Polecenia wykonuj w katalogu projektu (tam, gdzie jest ten plik).

```bash
python -m konwerter --lista                                    # macierz wspieranych par
python -m konwerter dane_testowe/studenci.csv                  # pokaż formaty dostępne dla pliku
python -m konwerter dane_testowe/studenci.csv --na json --do wyniki
python -m konwerter dane_testowe/produkty.json --na csv --do wyniki
python -m konwerter dane_testowe/produkty.json --na csv --do wyniki --nadpisz
```

Jeśli katalog podany w `--do` nie istnieje, zostanie utworzony. Gdy plik wynikowy już istnieje, program **nie nadpisuje go**,
tylko zapisuje wynik jako `nazwa (1).json`, `nazwa (2).json` … (chyba że podasz `--nadpisz`).
Błędy są wypisywane z przyczyną i podpowiedzią („Co zrobić: …”) oraz zapisywane do `konwerter.log`.

## Macierz wspieranych konwersji

| Grupa | Z | Na | Narzędzie | Znane ograniczenia |
|---|---|---|---|---|
| A – dane strukturalne | CSV | JSON | moduły `csv`, `json` (wbudowane) | wszystkie wartości trafiają do JSON jako tekst |
| A – dane strukturalne | JSON | CSV | moduły `csv`, `json` (wbudowane) | tylko płaska tablica obiektów, bez zagnieżdżeń |

## Semantyka CSV ↔ JSON

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

**Wyjściowy CSV**: UTF-8 z BOM (Excel poprawnie pokazuje polskie znaki), separator `,`,
`null` → pusta komórka, `true`/`false` → `true`/`false`.
**Wyjściowy JSON**: UTF-8, polskie znaki zapisane wprost (bez `ł`), wcięcie 2 spacje.

Wynik jest zapisywany najpierw do pliku `*.part`, a nazwa docelowa pojawia się dopiero po sukcesie –
po błędzie nie zostaje niepełny plik.

## Struktura projektu

```
konwerter/
  core.py               rejestr konwerterów, ConversionRequest, validate(), execute()
  errors.py             wspólny model błędów (przyczyna + podpowiedź)
  cli.py, __main__.py   uruchamianie z wiersza poleceń
  converters/
    structured.py       Grupa A: CSV <-> JSON
tests/                  testy pytest
dane_testowe/           przykładowe pliki wejściowe
```

Dodanie nowej pary formatów = funkcja z dekoratorem `@converter("docx", "pdf")` w module
w `konwerter/converters/` – bez zmian w rdzeniu i interfejsie.

## Dane testowe

| Plik | Co sprawdza | Oczekiwany wynik |
|---|---|---|
| `studenci.csv` | separator `;`, polskie znaki, puste wartości, `;` i `"` w cudzysłowie, zera wiodące | poprawny JSON z 3 obiektami, dane bez zmian |
| `produkty.json` | liczby, `true/false`, `null`, różne zestawy kluczy, przecinek w tekście | CSV z 5 kolumnami, brakujące pola puste |
| `bledny.json` | przecinek przed `}` | komunikat „Niepoprawny JSON … (wiersz 3, kolumna …)”, brak pliku wynikowego |
| `zagniezdzony.json` | obiekt w obiekcie | komunikat o nieobsługiwanym zagnieżdżeniu |
| `zla_liczba_kolumn.csv` | wiersz z nadmiarowym polem | komunikat „Wiersz 3: 4 pól, a nagłówek ma 3 kolumn” |

## Testy

```bash
python -m pytest -v
```

Testy automatyczne obejmują: `validate()`, `available_targets()`, politykę nadpisywania, oba konwertery
(poprawne dane, polskie znaki, puste wartości, BOM, pola wieloliniowe, błędne i uszkodzone pliki) oraz
test „w obie strony” CSV → JSON → CSV.

## Wykorzystane źródła i narzędzia AI

- Dokumentacja Pythona: [`csv`](https://docs.python.org/3/library/csv.html),
  [`json`](https://docs.python.org/3/library/json.html), [`pathlib`](https://docs.python.org/3/library/pathlib.html)
- Szkielet rejestru konwerterów oparty na kodzie inspiracyjnym z instrukcji projektu.


## Dziennik zmian

Zobacz [CHANGELOG.md](CHANGELOG.md) oraz historię w repozytorium Git.
