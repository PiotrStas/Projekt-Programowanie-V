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
