# Plan testów i lista zrzutów ekranu

## Wyniki (24.11.2026, konto Make Free, eu1)

| # | Wynik |
|---|---|
| T1 ok | ✅ faktura FV/2026/11/…, numer przesyłki, mail z potwierdzeniem, stan −1 |
| T2 invalid | ✅ 4/4 (kod pocztowy, 2× telefon, e-mail) w `Błędy`, mail do obsługi, brak faktury |
| T3 risk | ✅ 3/3 w `Do weryfikacji` (135 pkt, 6 powodów), alert na Slacku |
| T4 stockout | ✅ `brak towaru: Kreatyna monohydrat 500 g`, mail o opóźnieniu, stan bez zmian |
| T5 duplicate | ✅ jedna faktura, w `Błędy` wpis „duplikat” |
| T6 mix 21 | ✅ 21/21 tras zgodnych z manifestem, 0 błędów, D2 średnio ok. 3,7 s |
| T8 scenariusz 03 | ✅ 2 maile (NutriPol: 3 poz., VitaLab: 1 poz.), drugie uruchomienie: 0 maili |
| T7 awaria API | nie wykonano (wymaga wyłączenia Mock API w trakcie; Break handler jest skonfigurowany) |


## Przypadki testowe

Każdy przypadek uruchamiasz symulatorem. W kolumnie `oczekiwana_trasa` w pliku `runs/run_*.csv` jest to,
co *powinien* zrobić Make. Porównaj to z historią wykonań scenariusza i z arkuszem.

| # | Polecenie | Oczekiwana trasa | Co sprawdzić |
|---|---|---|---|
| T1 | `--scenario ok` | D2 realizacja | wiersz w `Zamówienia` z nr faktury i przesyłki, mail z potwierdzeniem, niższy `stan` w `Magazyn` |
| T2 | `--scenario invalid` (×4, losuje e-mail / kod / telefon / paczkomat) | B błędne dane | wiersz w `Błędy` z opisem problemu, mail do obsługi, **brak** faktury |
| T3 | `--scenario risk` | C do weryfikacji | wiersz w `Do weryfikacji` z 135 pkt i 6 powodami, alert na Slacku |
| T4 | `--scenario stockout` | D1 brak towaru | wiersz `brak towaru: Kreatyna monohydrat 500 g`, mail o opóźnieniu, stan **bez zmian** |
| T5 | `--scenario duplicate` | D2, potem A | jedna faktura, w `Błędy` wpis „duplikat” |
| T6 | `--scenario mix --count 20` | wszystkie | liczba wierszy w arkuszach zgodna z manifestem |
| T7 | wyłącz scenariusz Mock API i wyślij `ok` | D2 z błędem | wykonanie w *Incomplete executions*; po włączeniu mocka i ponowieniu: zamówienie zrealizowane raz |
| T8 | uruchom scenariusz 03 (*Run once*) po T6 | — | mail do każdego dostawcy z produktami poniżej progu, `status_zamowienia` = `zamówione`; drugie uruchomienie nic nie wysyła |

Wyniki wpisz do tabeli w README (sekcja „Wyniki testów”). Prawdziwe liczby z własnych testów są mocniejsze niż deklaracje.

## Zrzuty ekranu do `docs/screenshots/`

| Plik | Co pokazać |
|---|---|
| `01-scenariusz-glowny.png` | cały scenariusz 01, wszystkie trasy widoczne, nazwy modułów czytelne (zoom ok. 80%) |
| `02-historia-wykonan.png` | *History* scenariusza 01 po teście mix: zielone wykonania, czasy trwania |
| `03-trasa-weryfikacji.png` | jedno wykonanie z trasą C: bąbelki z liczbą operacji, filtr przepuszczony |
| `04-arkusz-zamowienia.png` | zakładka `Zamówienia` z numerami faktur i przesyłek |
| `05-arkusz-magazyn.png` | `Magazyn` z czerwonymi wierszami poniżej progu |
| `06-mail-potwierdzenie.png` | mail do klienta (Gmail) |
| `07-slack.png` | kanał `#zamowienia` z alertami |
| `08-mail-dostawca.png` | mail z zamówieniem do dostawcy (tabela) |
| `09-terminal-symulator.png` | wynik `send_orders.py --scenario mix` z kolumną oczekiwanej trasy |

Na zrzutach zasłoń adresy webhooków. Każdy, kto zna adres, może wysyłać do scenariusza dane.

## Eksport blueprintów

Po zakończeniu testów wyeksportuj **swoje** działające scenariusze (menu `…` › *Export blueprint*) do
`make/blueprints/01-przyjecie-zamowienia.blueprint.json` i `03-stany-magazynowe.blueprint.json`.
Przed commitem usuń z nich adresy webhooków i e-maile (wyszukaj `hook.` i `@`).
