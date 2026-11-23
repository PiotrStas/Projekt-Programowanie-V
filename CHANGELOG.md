# Dziennik zmian

## Lab 6 – profil danych i pipeline czyszczenia
- Wczytywanie CSV (`studio/loader.py`): separator `,` `;` lub tabulator wykrywany z nagłówka,
  kontrolowane błędy kodowania, wadliwego wiersza, pustego pliku i powtórzonych kolumn.
- Profil danych (`studio/profile.py`): rozmiar, typy, statystyki opisowe, braki (liczba i %),
  pełne duplikaty, liczba unikalnych wartości.
- Reguły jakości (`studio/rules.py`): zakres poprawnych wartości (`RangeRule`) i wartości odstające IQR;
  reguły tylko wykrywają problemy, niczego nie zmieniają.
- Czyszczenie (`studio/cleaning.py`): duplikaty (pełne lub wg klucza), braki (mediana, średnia,
  dominanta, stała, usunięcie wierszy), wartości poza zakresem (na brak, przycięcie, usunięcie),
  wartości odstające (oznaczenie, przycięcie, usunięcie). Każda operacja zmienia tylko wskazaną kolumnę.
- Sesja (`studio/session.py`): dane surowe i bieżące, dziennik operacji (parametry, czas,
  wiersze przed/po, liczba zmienionych rekordów), reset bez ponownego wczytywania, eksport CSV.
- Skrypt `python -m studio.pipeline`: czyści California Housing, zapisuje `cleaned.csv`,
  raport zmian, profil i raport jakości przed/po.
- 52 testy pytest na małych, ręcznie kontrolowanych danych i plikach `test_01`–`test_06`.

## Lab 7 – wykresy i korelacja
- `studio/charts.py`: histogram, wykres punktowy (z korelacją r i kolorem wg kategorii),
  pudełkowy (opcjonalnie wg kategorii) i słupkowy (liczebność lub średnia/mediana/suma);
  macierz korelacji (Pearson/Spearman) i lista najsilniejszych par z opisem siły.
- Każda funkcja zwraca `matplotlib.figure.Figure` (bez pyplot i stanu globalnego) – gotowe
  do osadzenia w Tkinter i zapisu do PNG/PDF/SVG (`save_figure`).
- Walidacja kolumn: tekst, kolumna stała, pusta lub z za dużą liczbą kategorii blokuje wykres
  z komunikatem; czytelne opisy osi z jednostkami dla zbioru California Housing.
- `build_chart(df, typ, **parametry)` – jeden punkt wejścia dla GUI.
- Wykresy przed/po czyszczeniu (`before_after_figure`, skala logarytmiczna dla histogramu).
- Skrypt `python -m studio.wykresy`: 8 wykresów + korelacja w PDF/SVG + `wnioski.txt`
  z interpretacją (korelacja ≠ przyczynowość).
- 21 nowych testów (razem 73).

## Lab 8 – okno programu (Tkinter/ttk)
- `python -m studio` otwiera okno: wczytanie CSV, zakładki Podgląd, Profil, Jakość i Czyszczenie.
- Podgląd pierwszych 200 wierszy danych bieżących; profil kolumn (z przełącznikiem „dane surowe”).
- Zakładka Jakość: reguła zakresu dla wybranej kolumny i raport IQR – tylko wykrywanie, bez zmian danych.
- Zakładka Czyszczenie: wybór operacji, wariantu, kolumny i parametrów; listy kolumn filtrowane
  wg typu (np. mediana tylko dla liczb); dziennik zmian w tabeli; reset do danych surowych.
- Stan aplikacji w obiekcie `StudioApp` (bez zmiennych globalnych); `refresh_all()` odświeża
  wszystkie kontrolki po każdej zmianie zbioru.
- Błędny plik lub parametr -> okienko z przyczyną i podpowiedzią; poprzednie dane zostają.
- Logika okna bez Tkintera w `studio/gui_logic.py`; 25 nowych testów (logika + prawdziwe okno), razem 98.
