# Słownik KPI

Wszystkie kwoty **netto w PLN**. Definicje są zaimplementowane w jednym miejscu (`src/kpis.py`), z którego korzystają raport i (w tej samej logice) dashboard – dzięki temu liczby w obu miejscach są spójne.

| Wskaźnik | Wzór | Dlaczego ważny |
|---|---|---|
| **Przychód netto** | Σ (ilość × cena × (1 − rabat)) dla zamówień niezwróconych | Podstawowa miara skali sprzedaży. Zwroty są odejmowane, żeby nie zawyżać wyniku. |
| **Zamówienia** | liczba unikalnych zamówień bez anulowanych i testowych | Wolumen – razem z AOV wyjaśnia zmianę przychodu. |
| **AOV** (średnia wartość zamówienia) | przychód netto / liczba niezwróconych zamówień | Pokazuje efekt cross-sellingu, zestawów, progów darmowej dostawy. |
| **Marża brutto** | przychód − koszt zakupu towaru (COGS) − prowizje kanałów | Ile realnie zostaje ze sprzedaży. Allegro (11%) i Amazon (15%) mają wyższe prowizje niż sklep własny (1,5% bramka płatności). |
| **Marża brutto %** | marża brutto / przychód netto | Porównanie rentowności kategorii i kanałów. |
| **Wydatki reklamowe** | Meta Ads + Google Ads (→ Sklep WWW), Allegro Ads (→ Allegro), Amazon Ads (→ Amazon.pl) | Koszt pozyskania sprzedaży. |
| **ROAS** | przychód netto / wydatki reklamowe | Skuteczność reklam. Próg alertu: 3,0. |
| **Marża po reklamie** (contribution margin) | marża brutto − wydatki reklamowe | Najlepsza pojedyncza miara „czy kanał zarabia”. Kanał z wysokim przychodem i niskim ROAS może dawać mniej niż mniejszy kanał. |
| **Odsetek zwrotów** | zamówienia zwrócone / wszystkie zamówienia | Sygnał problemów z jakością, opisem produktu lub logistyką. Próg alertu: 5%. |
| **Klienci nowi / powracający** | nowy = pierwsze zamówienie w historii danych | Udział powracających to miara lojalności – w suplementach kluczowa (produkty się kończą). |
| **CAC** | wydatki reklamowe / liczba nowych klientów | Koszt pozyskania nowego klienta (uproszczony – całość budżetu przypisana nowym). |

## Reguły alertów (raport tygodniowy)

| Alert | Warunek | Poziom |
|---|---|---|
| Spadek przychodu kanału | zmiana t/t ≤ −15% **i** spadek ≥ 2000 zł (filtr szumu w małych kanałach) | Wymaga działania |
| Możliwy brak towaru | produkt sprzedawał się w kanale **w każdym** z 4 poprzednich tygodni, średnio ≥ 6 szt./tydz., a w bieżącym 0 szt. | Wymaga działania |
| Niski ROAS | ROAS kanału < 3,0 | Do obserwacji |
| Wysoki odsetek zwrotów | > 5% zamówień w tygodniu | Do obserwacji |
| Najszybciej rosnący kanał | najwyższy wzrost t/t, jeśli > 5% | Pozytywne |

Progi są w `src/config.py` – właściciel biznesu może je zmienić bez dotykania logiki.
