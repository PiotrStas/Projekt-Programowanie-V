# Studio jakości i wizualizacji danych

**Projekt 2 – Programowanie V**, Politechnika Opolska, Wydział Informatyki
**Autor:** Piotr Staś (nr albumu 105534)

Aplikacja desktopowa (Python + Tkinter/ttk), która prowadzi od wczytania pliku CSV przez
profil danych, reguły jakości i czyszczenie aż do wykresów i eksportu wyników.
Każda zmiana danych jest zapisywana w dzienniku, więc widać, co dokładnie zmieniło zbiór
i ilu rekordów to dotyczyło. Dane surowe zostają nietknięte – w każdej chwili można wrócić
do nich przyciskiem „Reset”.

---

## Wymagania

| Składnik | Wersja | Do czego |
|---|---|---|
| Python | 3.10 lub nowszy | aplikacja (Tkinter jest w standardowej instalacji na Windows) |
| pandas | 2.2 lub nowszy | wczytywanie, profil i czyszczenie danych |
| matplotlib | 3.8 lub nowszy | wykresy, osadzanie w oknie, zapis PNG/PDF/SVG |
| seaborn | 0.13 lub nowszy | wykres punktowy, pudełkowy i macierz korelacji |
| pytest | 7.0 lub nowszy | testy |

Na Linuksie Tkinter instaluje się osobno, np. `sudo apt install python3-tk`.

## Instalacja

Wszystkie polecenia wykonuje się w głównym folderze repozytorium (gałąź `projekt-2`).

```bash
git clone <adres-repozytorium>
cd Projekt-Programowanie-V
git checkout projekt-2
python -m pip install -r requirements.txt
```

Sprawdzenie:

```bash
python -m pytest tests
```

Oczekiwany wynik: `105 passed`.

## Uruchomienie

### Okno programu

```bash
python -m studio
```

1. **Wczytaj CSV…** – plik z separatorem `,`, `;` albo tabulatorem, w kodowaniu UTF-8.
2. **Podgląd** – pierwsze 200 wierszy danych bieżących.
3. **Profil** – rozmiar, typy, statystyki, braki (liczba i %), duplikaty, liczba unikalnych wartości.
   Przełącznik „pokaż dane surowe” pokazuje stan sprzed czyszczenia.
4. **Jakość** – reguła zakresu dla wybranej kolumny i raport wartości odstających (IQR).
   Raport niczego nie zmienia, tylko pokazuje, ile rekordów narusza regułę.
5. **Czyszczenie** – operacja, wariant, kolumna i parametry → **Wykonaj operację**.
   Pod formularzem jest dziennik zmian. Listy kolumn pokazują tylko kolumny pasujące do operacji.
6. **Wykresy** – typ wykresu, dane (po czyszczeniu albo surowe), kolumny → **Rysuj**.
   Wykres pojawia się w oknie; **Zapisz wykres…** zapisuje go do PNG, PDF albo SVG.
7. **Zapisz CSV…** i **Zapisz raport zmian…** (górny pasek) – eksport danych i dziennika.

Błędy (zły plik, zły parametr, zła kolumna do wykresu, błąd zapisu) kończą się okienkiem
z przyczyną i podpowiedzią. Program działa dalej, a poprzednie dane zostają.

### Skrypty bez okna

```bash
python -m studio.pipeline      # czyszczenie California Housing + raport przed/po -> wyniki/
python -m studio.wykresy       # wykresy przed/po + korelacja -> wyniki/wykresy/
```

## Obsługiwane funkcje

**Wczytywanie:** separator wykrywany z nagłówka (`,` `;` tab), UTF-8 z BOM i bez.
Kontrolowane błędy: brak pliku, złe kodowanie, wiersz z inną liczbą pól (z numerem wiersza),
pusty plik, sam nagłówek, powtórzone nazwy kolumn.

**Czyszczenie:**

| Operacja | Warianty |
|---|---|
| duplikaty | pełne duplikaty albo według wybranej kolumny (zostaje pierwsze wystąpienie) |
| uzupełnianie braków | mediana, średnia (tylko liczby), dominanta, stała wartość |
| usuwanie braków | wiersze z brakiem w wybranej albo dowolnej kolumnie |
| reguła zakresu | wartości spoza [min, max]: zamiana na brak, przycięcie do granic, usunięcie wierszy |
| wartości odstające (IQR) | tylko oznaczenie (nowa kolumna `<kolumna>_odstajaca`), przycięcie, usunięcie |

Każda operacja zmienia tylko wskazaną kolumnę i dopisuje do dziennika: nazwę, parametry,
czas, liczbę wierszy przed i po oraz liczbę zmienionych rekordów.

**Wykresy:** histogram, punktowy (z kolorem wg kategorii i współczynnikiem r w tytule),
pudełkowy (opcjonalnie wg kategorii), słupkowy (liczebność albo mediana wartości w kategorii),
macierz korelacji. Kolumna tekstowa, stała albo z ponad 30 kategoriami nie trafia na listę,
a gdyby jednak została wybrana – wykres jest blokowany z komunikatem.

## Reguły i decyzje dla zbioru California Housing

W pliku `california_housing_z_problemami.csv` (20 670 × 10) są celowo dodane błędy.
Skrypt `studio.pipeline` stosuje następujące kroki:

| Krok | Uzasadnienie | Zmienione rekordy |
|---|---|---|
| usunięcie pełnych duplikatów | identyczne wiersze to błąd zapisu | 30 |
| `HouseAge` ∈ [0, 100] → poza zakresem na brak | wiek budynku nie może być ujemny (w danych jest -5) | 40 |
| `AveRooms` ∈ [0, 200] → poza zakresem na brak | ponad 200 pokoi na mieszkanie jest nierealne; w oryginalnym zbiorze maksimum to ok. 142, w danych są sztuczne wartości 1000 | 50 |
| mediana dla `MedInc`, `HouseAge`, `AveRooms` | mediana nie jest zaburzana przez wartości skrajne | 80 / 40 / 50 |
| usunięcie wierszy bez `Region` | regionu nie da się sensownie odgadnąć | 40 |
| IQR (k = 1,5) dla `AveOccup` i `Population` – tylko oznaczenie | skrajne wartości mogą być prawdziwe (duże osiedla, akademiki) | 710 / 1195 |

Wynik: 20 600 wierszy, 0 braków, 0 duplikatów.

**Czego celowo nie zmieniam:** `MedHouseVal = 5.00001` (994 wiersze) i `HouseAge = 52`
(1271 wierszy) to górne limity z oryginalnego spisu, a nie błędy. Metoda IQR oznacza część
z nich jako odstające, ale usunięcie ich zniekształciłoby dane.

**Korelacja:** najsilniejsze pary to Latitude–Longitude (r = −0,93, wynika z kształtu Kalifornii),
AveRooms–AveBedrms (+0,85) i MedInc–MedHouseVal (+0,69). Korelacja nie oznacza przyczynowości –
dochód i ceny domów mogą zależeć od wspólnego czynnika, np. lokalizacji.

## Przykładowe wyniki

Folder [`przyklad_wynikow/`](przyklad_wynikow/) zawiera wyniki dla zbioru California Housing:
`cleaned.csv`, `raport_zmian.csv`, `raport.txt` (profil i reguły przed/po), wykresy
`01_aveRooms_przed_po.png`, `04_punktowy_medInc_medHouseVal.png`, `08_korelacja` (PNG, PDF, SVG)
oraz `wnioski.txt` z interpretacją korelacji.

## Dane testowe

| Plik | Co sprawdza | Oczekiwany wynik |
|---|---|---|
| `test_01_przecinek.csv` | separator `,` | 3 wiersze × 3 kolumny |
| `test_02_srednik.csv` | separator `;` | 3 wiersze × 3 kolumny |
| `test_03_braki_duplikaty.csv` | braki liczbowe i tekstowe, para duplikatów | 3 braki, 1 duplikat; po usunięciu 4 wiersze |
| `test_04_zakres_outlier.csv` | `HouseAge = -5`, `AveRooms = 1000` | reguła zakresu wykrywa 1 rekord, IQR wykrywa 1 rekord |
| `test_05_bledne_wiersze.csv` | wiersz z dodatkowym polem | komunikat „Wadliwy wiersz 3…”, program działa dalej |
| `test_06_stala_tekst.csv` | stała kolumna i kolumna tekstowa | histogram zablokowany z komunikatem |
| `california_housing_z_problemami.csv` | zbiór referencyjny | jak w tabeli „Reguły i decyzje” |

## Raport testów

`python -m pytest tests` – **105 testów, wszystkie zaliczone** (Windows, Python 3.13).

| Plik | Zakres |
|---|---|
| `test_loader.py` | separatory, BOM, złe kodowanie, wadliwy wiersz, pusty plik, powtórzone kolumny |
| `test_profile_rules.py` | profil, reguła zakresu, IQR, raport jakości, niepoprawne parametry reguły |
| `test_cleaning_session.py` | wszystkie operacje, nienaruszone inne kolumny, dziennik, reset, eksport i ponowny odczyt, powtarzalność pipeline'u |
| `test_charts.py` | cztery typy wykresów, korelacja, blokada złych kolumn, zapis PNG/PDF/SVG |
| `test_gui.py` | logika okna oraz prawdziwe okno: wczytanie, błędny plik, odświeżanie list, operacje, wykres w oknie i jego podmiana, eksport z okna |

Testy używają małych, ręcznie przygotowanych danych. Testy okna są pomijane na komputerze bez ekranu.

**Minimalna macierz testów z instrukcji:**

| Przypadek | Oczekiwany rezultat | Wynik |
|---|---|---|
| CSV z przecinkiem i średnikiem | poprawna liczba kolumn | ✅ `test_01`, `test_02` |
| braki liczbowe i tekstowe | strategia działa, raport podaje liczbę zmian | ✅ mediana/dominanta/stała/usunięcie, dziennik |
| duplikaty | usuwane tylko pełne duplikaty albo wg klucza | ✅ kontrolowana para w `test_03` i teście z kluczem |
| wartość poza zakresem | reguła wykrywa rekord, nie zmienia danych bez decyzji | ✅ raport jakości + osobna operacja |
| stała lub nienumeryczna kolumna | wykres zablokowany z komunikatem | ✅ `test_06`, test okna |
| eksport | CSV da się ponownie wczytać, PNG/PDF/SVG się otwierają | ✅ testy eksportu z okna i z sesji |

## Architektura

```
studio/
  loader.py      wczytywanie CSV i kontrola błędów
  profile.py     profil danych
  rules.py       reguła zakresu, IQR, raport jakości
  cleaning.py    operacje czyszczenia (czyste funkcje, pracują na kopii)
  session.py     DataSession: dane surowe, bieżące, dziennik, reset, eksport
  charts.py      wykresy – funkcje zwracają Figure
  gui_logic.py   logika okna bez Tkintera (listy kolumn, parametry)
  gui.py         okno Tkinter/ttk
  pipeline.py    skrypt czyszczący (Lab 6)
  wykresy.py     skrypt z wykresami (Lab 7)
tests/           testy pytest
dane_testowe/    pliki testowe i zbiór referencyjny
przyklad_wynikow/ przykładowe wyniki
```

Okno nie zawiera logiki danych – wywołuje tylko metody `DataSession` i funkcje z `charts.py`.
Stan aplikacji jest w obiekcie `StudioApp`, bez zmiennych globalnych. Wykresy powstają jako
`matplotlib.figure.Figure` (bez `pyplot`), więc ten sam obiekt trafia do okna przez
`FigureCanvasTkAgg` albo do pliku. Przed narysowaniem nowego wykresu poprzedni jest usuwany z okna.

## Znane ograniczenia

- Obsługiwane jest tylko kodowanie UTF-8 – plik w ANSI trzeba zapisać ponownie jako CSV UTF-8.
- Podgląd pokazuje 200 pierwszych wierszy.
- Wykres słupkowy przyjmuje maksymalnie 30 kategorii.
- Nie ma cofania pojedynczej operacji – jest reset do danych surowych.
- Polski Excel może otworzyć wynikowy CSV (separator `,`) w jednej kolumnie; wtedy
  Dane → Z pliku tekstowego/CSV.

## Źródła i narzędzia

- [pandas.read_csv](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html), [Pandas User Guide](https://pandas.pydata.org/docs/user_guide/index.html)
- [Matplotlib – Embed in Tk](https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_tk_sgskip.html)
- [Seaborn – Tutorial](https://seaborn.pydata.org/tutorial.html)
- [tkinter.ttk](https://docs.python.org/3/library/tkinter.ttk.html), [pytest](https://docs.pytest.org/)
- Dane: California Housing (spis USA z 1990 r., scikit-learn) z błędami dodanymi przez prowadzącego.
- Wzorzec `DataSession` oparty na kodzie inspiracyjnym z instrukcji projektu.
- Narzędzia AI: Claude (Anthropic) – pomoc przy kodzie i dokumentacji.

## Historia zmian

Zobacz [CHANGELOG.md](CHANGELOG.md) oraz historię commitów na gałęzi `projekt-2`.
