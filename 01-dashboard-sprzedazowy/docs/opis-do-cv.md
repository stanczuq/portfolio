# Jak pokazać ten projekt w CV, na LinkedIn i na rozmowie

## Do CV (sekcja „Projekty”)

**Dashboard sprzedażowy z automatycznym raportem tygodniowym | Python, pandas, Make, GitHub Actions**
- Zaprojektowałem pipeline ETL łączący dane z 3 kanałów sprzedaży (sklep WWW, Allegro, Amazon) i 4 platform reklamowych; automatyczne czyszczenie ~24 tys. wierszy (duplikaty, formaty dat, testowe zamówienia) z raportem jakości danych.
- Zdefiniowałem KPI pod decyzje biznesowe (marża po prowizjach i po reklamie, ROAS, zwroty, retencja) w jednym module używanym przez dashboard i raport.
- Zbudowałem interaktywny dashboard HTML/SVG (filtry, porównanie okresów, heatmapa zakupów, wnioski automatyczne) działający offline bez licencji BI.
- Zautomatyzowałem cotygodniowy raport PDF z alertami (spadki kanałów, braki towaru, niski ROAS) i dystrybucję przez Make: e-mail, Slack, Google Sheets, zadania w Trello.

Wersja skrócona (1 linijka):
> Automatyczny raport sprzedaży e-commerce dla 3 kanałów: ETL w Pythonie, dashboard KPI, alerty braków towaru i dystrybucja przez Make (e-mail, Slack, Trello).

## Post na LinkedIn (szkic)

> Ile czasu zajmuje Ci poniedziałkowy raport sprzedaży z Allegro, sklepu i Amazona? 📊
>
> Zbudowałem projekt, który robi to sam: co poniedziałek o 7:00 pobiera dane, czyści je, liczy marżę po prowizjach i po reklamie, wykrywa anomalie i wysyła raport PDF na maila, podsumowanie na Slacka i zadania do Trello.
>
> Najciekawszy moment: w danych testowych przychód z Allegro spadł o 17%. Raport sam wskazał przyczynę: bestseller (kreatyna 500 g) nie sprzedał się ani razu przez cały tydzień, co sugeruje brak towaru albo wygasłą ofertę. To różnica między „mamy spadek” a „sprawdź ofertę X”.
>
> Stack: Python + pandas, dashboard w czystym HTML/SVG, Make, GitHub Actions.
> Link do repozytorium w komentarzu 👇
>
> #ecommerce #automatyzacja #make #python #analizadanych

## Na rozmowie: jak opowiedzieć projekt w 2 minuty

1. **Problem**: właściciel sklepu z 3 kanałami traci kilka godzin tygodniowo na ręczny raport, a o problemach dowiaduje się za późno.
2. **Decyzja architektoniczna**: Python liczy (powtarzalnie, wersjonowane), Make komunikuje (biznes sam zmienia odbiorców i treści).
3. **Pokaż dashboard**: przełącz na „7 dni” i pokaż wnioski automatyczne z alertem braku towaru.
4. **Pokaż jedną liczbę, która zmienia decyzję**: Allegro ma niższy przychód niż sklep, ale wyższą marżę po reklamie.
5. **Co dalej u klienta**: podpięcie prawdziwych API, stany magazynowe, komentarz generowany przez AI.

Pytania, na które warto mieć odpowiedź:
- *Dlaczego nie Power BI / Looker Studio?* Zero licencji, działa offline, pełna kontrola. Te same dane (`orders_clean.csv`) można podpiąć do BI, gdy firma urośnie.
- *Skąd progi alertów?* Są w `config.py` i ustala je biznes. Filtr minimalnej kwoty spadku usuwa fałszywe alarmy w małych kanałach.
- *Jak wykrywasz brak towaru bez danych z magazynu?* Produkt sprzedawał się w kanale w każdym z 4 ostatnich tygodni, a teraz 0 sztuk. Rozszerzeniem jest potwierdzenie stanem magazynowym.
