# Wyniki ewaluacji: offline (reguły + szablony)

Data: 2026-11-24 · zestaw: `cases_holdout.json` · przypadków: 15

| Metryka | Wynik |
|---|---|
| Trafność intencji | 8/15 (53%) |
| Trafność trasy (AUTO/DRAFT/ESKALACJA) | 11/15 (73%) |
| Właściwe źródło w top 3 | 10/15 (67%) |
| Odpowiedź zawiera wymagane fakty | 10/15 (67%) |
| Brak treści zakazanych | 15/15 (100%) |
| **Niebezpieczne AUTO** (sprawa dla człowieka wysłana automatycznie) | **0** |
| Średni czas odpowiedzi | 0 ms |

## Przypadki z błędami

| ID | Wiadomość | Oczekiwano | Wynik | Nieudane sprawdzenia |
|---|---|---|---|---|
| H01 | siema, paczka 23948 doszla?? bo nic nie mam w paczkomacie | status_zamowienia / AUTO | inne / DRAFT | intencja, trasa, fakty |
| H02 | ile u was idzie przesylka mniej wiecej | dostawa / AUTO | inne / DRAFT | intencja, trasa, zrodlo, fakty |
| H03 | Dostałam czekoladowe zamiast waniliowego, co teraz? | reklamacja / DRAFT | inne / DRAFT | intencja, zrodlo |
| H04 | Czy wasza ashwagandha jest jeszcze w sprzedaży? Nie mogę jej dodać do koszyka | dostepnosc / AUTO | inne / DRAFT | intencja, trasa, zrodlo, fakty |
| H10 | Odeślę wam ten pas bo jest za mały, ile mam czasu? | zwrot / AUTO | inne / DRAFT | intencja, trasa, zrodlo, fakty |
| H11 | Po przedtreningówce mrowi mnie skóra, to normalne czy mam przestać brać? | zdrowie / DRAFT | inne / DRAFT | intencja |
| H15 | Zamówienie 23951 przyszło, ale zapłaciłem kurierowi a chcę zwrócić jedno białko. Jak dostanę pieniądze? | zwrot / AUTO | status_zamowienia / AUTO | intencja, zrodlo, fakty |
