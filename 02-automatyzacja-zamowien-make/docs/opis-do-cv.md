# Jak pokazać ten projekt w CV, na LinkedIn i na rozmowie

## Do CV (sekcja „Projekty”)

**Automatyzacja obsługi zamówień e-commerce | Make, REST API, Google Sheets, Python**
- Zaprojektowałem i zbudowałem w Make proces od zamówienia do wysyłki (29 modułów, 5 tras): walidacja danych klienta, ocena ryzyka, kontrola magazynu, faktura (Fakturownia API), przesyłka (InPost ShipX API) i komunikacja z klientem.
- Wdrożyłem punktowy model ryzyka (6 sygnałów, m.in. jednorazowy e-mail, pobranie przy wysokiej kwocie, hurtowe ilości), który wstrzymuje podejrzane zamówienia do decyzji człowieka z alertem na Slacku.
- Zabezpieczyłem proces przed typowymi awariami: idempotencja przez data store (ponowienia webhooków), przetwarzanie sekwencyjne, ponowienia wywołań API i zdejmowanie stanu dopiero po sukcesie.
- Zautomatyzowałem zamówienia do dostawców: codzienny scenariusz grupuje produkty poniżej progu i wysyła jeden mail z tabelą do każdego dostawcy.
- Napisałem w Pythonie symulator webhooków Shopify z przypadkami brzegowymi i oczekiwanym wynikiem dla każdego zamówienia; zgodność tras w teście na żywo: 21/21, zero błędów, średnio 3,7 s na zamówienie.

Wersja skrócona (1 linijka):
> Automatyzacja zamówień e-commerce w Make: walidacja, ocena ryzyka, magazyn, faktura i etykieta InPost przez API, maile do klientów i zamówienia do dostawców.

## Post na LinkedIn (szkic)

> Ile kliknięć dzieli zamówienie w sklepie od paczki z etykietą? 📦
>
> W małym e-commerce zwykle kilkanaście, w 4 różnych systemach. Zbudowałem w Make proces, który robi to sam: sprawdza dane klienta, stan magazynu, wystawia fakturę, tworzy przesyłkę InPost i wysyła klientowi maila z numerem śledzenia.
>
> Najciekawsze było projektowanie wyjątków, a nie „szczęśliwej ścieżki”:
> 🔁 Shopify ponawia webhooki, więc bez pamięci przetworzonych zamówień klient dostałby dwie faktury
> 🚨 zamówienie za 1800 zł od nowego klienta, z jednorazowego maila, za pobraniem, do innego miasta niż faktura: 135 pkt ryzyka, wstrzymane, alert na Slacku
> 📉 wyprzedany produkt: klient od razu dostaje informację, zamiast czekać na niepełną paczkę
>
> Do testów napisałem symulator zamówień w Pythonie, który dla każdego przypadku zapisuje, co automatyzacja *powinna* zrobić.
>
> Link do repozytorium w komentarzu 👇
>
> #ecommerce #automatyzacja #make #nocode #integracje

## Na rozmowie: jak opowiedzieć projekt w 2 minuty

1. **Problem**: ok. 5 minut ręcznej pracy na zamówienie w 4 systemach, a błędy wychodzą dopiero przy zwrocie paczki.
2. **Pokaż scenariusz 01** i opowiedz trasy routera: duplikat, błędne dane, ryzyko, brak towaru, wysyłka.
3. **Jedna decyzja projektowa**: stan magazynu zdejmowany na końcu, po fakturze i przesyłce, plus ponowienia na API. Awaria w połowie nie psuje danych.
4. **Pokaż test**: terminal z symulatorem (oczekiwane trasy) obok historii wykonań w Make.
5. **Co dalej u klienta**: Allegro jako drugie źródło zamówień, zatwierdzanie wstrzymanych zamówień jednym kliknięciem, śledzenie statusu przesyłki.

Pytania, na które warto mieć odpowiedź:
- *Dlaczego mock zamiast prawdziwej Fakturowni?* Mock odpowiada w formacie prawdziwego API, a zapytania wysyłam już w docelowym formacie. U klienta zmieniam 2 adresy i token. Nie zużywam też limitów triala w trakcie testów.
- *Co, jeśli dwa zamówienia przyjdą naraz?* Sequential processing w ustawieniach scenariusza. Przy dużej skali magazyn trzeba przenieść do systemu z transakcjami (np. BaseLinker), bo Google Sheets nie blokuje wierszy.
- *Skąd progi ryzyka?* Na start z typowych problemów branży (nieodebrane pobrania, odsprzedawcy). U klienta kalibruję je na historii: ile zamówień o danym profilu nie zostało odebranych.
- *Ile to kosztuje miesięcznie?* Ok. 24 operacje na zrealizowane zamówienie, czyli przy 40 zamówieniach dziennie ok. 29 tys. operacji miesięcznie. Porównaj aktualny cennik Make z ok. 60 godzinami ręcznej pracy miesięcznie, które ta automatyzacja zastępuje (przed rozmową sprawdź ceny planów).
- *Jak weryfikujesz, że webhook naprawdę jest od Shopify?* Na produkcji: weryfikacja podpisu HMAC z nagłówka `X-Shopify-Hmac-Sha256`. W demo adres webhooka jest traktowany jak sekret.
