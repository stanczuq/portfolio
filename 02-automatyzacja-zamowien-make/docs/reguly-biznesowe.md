# Reguły biznesowe: walidacja, ryzyko, magazyn

Reguły ustala biznes, a nie programista. Są zapisane w dwóch miejscach, które muszą być zgodne:
w Make (scenariusz 01, moduł 3) i w `simulator/rules.py`, który służy jako wyrocznia w testach.

## 1. Walidacja danych: zamówienie zatrzymane, obsługa dostaje maila

| Reguła | Warunek | Dlaczego |
|---|---|---|
| E-mail | niepusty i w formacie `x@y.zz` | bez maila klient nie dostanie faktury ani numeru przesyłki |
| Kod pocztowy | format `00-000` | InPost odrzuci przesyłkę z błędnym kodem |
| Telefon | 9 cyfr po usunięciu `+48`, spacji i myślników | wymagany przez InPost (SMS z kodem odbioru) |
| Pozycje | co najmniej 1 | ochrona przed pustym lub uszkodzonym webhookiem |
| Paczkomat | podany, gdy metoda dostawy to `inpost_locker` | bez punktu docelowego nie powstanie etykieta |

## 2. Ocena ryzyka: zamówienie wstrzymane od 50 pkt

| Sygnał | Punkty |
|---|---:|
| wartość zamówienia > 1500 zł | 30 |
| pierwsze zamówienie klienta i wartość > 600 zł | 15 |
| jednorazowa domena e-mail (mailinator, yopmail…) | 30 |
| inne miasto na fakturze niż w adresie dostawy | 25 |
| ≥ 10 sztuk jednego produktu | 20 |
| płatność za pobraniem i wartość > 800 zł | 15 |

Próg 50 oznacza, że **jeden sygnał nie wystarczy**. Duże zamówienie stałego klienta (30 pkt) albo prezent
wysłany do innego miasta (25 pkt) przechodzą automatycznie. Wstrzymane zostaje dopiero zamówienie z kilkoma
sygnałami naraz, np. nowy klient + jednorazowy e-mail + 12 szt. cytruliny za pobraniem.

Typowe zagrożenia w sklepie z suplementami, które ta reguła łapie:
- **nieodebrane pobrania**: koszt wysyłki w dwie strony i towar zamrożony na ok. 2 tygodnie,
- **hurtowe wykupywanie promocji** przez odsprzedawców (dużo sztuk jednego produktu),
- **wyłudzenia** na podstawione dane.

Wstrzymane zamówienie trafia do zakładki `Do weryfikacji`, a na Slacku pojawia się alert z powodami.
Człowiek wybiera decyzję z listy (Zatwierdź / Odrzuć).

## 3. Magazyn

- Stan sprawdzany jest **przed** wystawieniem faktury. Jeśli brakuje choć jednej pozycji, zamówienie czeka,
  a klient dostaje maila z informacją o opóźnieniu, zamiast paczki z brakami.
- Stan zdejmowany jest **po** utworzeniu faktury i przesyłki.
- Produkt ze stanem ≤ `prog_minimalny` jest raz dziennie zamawiany u dostawcy w ilości `ilosc_zamawiana`,
  jednym mailem na dostawcę.
- `KRE-500` (Kreatyna 500 g) startuje ze stanem 0. To nawiązanie do projektu „Dashboard sprzedażowy”, w którym
  raport tygodniowy wykrył prawdopodobny brak tego produktu na Allegro. Tutaj automatyzacja ten brak obsługuje.

## Co zmienić u prawdziwego klienta

- Progi ryzyka dopasować do historii zwrotów i nieodebranych paczek (np. ile pobrań > 800 zł nie zostało odebranych).
- Listę jednorazowych domen pobierać z publicznej listy zamiast trzymać ją w formule.
- Magazyn przenieść z Google Sheets do systemu magazynowego (np. Subiekt, BaseLinker), gdy zamówień jest więcej niż kilkaset dziennie.
