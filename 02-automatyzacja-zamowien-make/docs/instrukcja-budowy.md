# Instrukcja budowy scenariuszy w Make – moduł po module

Czas: ok. 3–4 godziny za pierwszym razem. Buduj w kolejności z tej instrukcji: Make nadaje modułom numery
w kolejności dodawania, a formuły odwołują się do nich (`{{2.wartosc}}` = pole `wartosc` z modułu nr 2).
Jeśli numer wyjdzie Ci inny, po prostu wybierz to samo pole z panelu mapowania.

**Konwencja nazw:** każdy moduł podpisz (prawy klik › *Rename*) tak jak w nagłówkach poniżej.
Na zrzutach ekranu od razu widać wtedy logikę procesu.

---

## Krok 0. Przygotowanie (20 min)

1. **Arkusz.** W Google Drive utwórz arkusz `VitaForge – Operacje` i zaimportuj `sheets/VitaForge_Operacje.xlsx`
   (Plik › Importuj › Prześlij › *Zastąp arkusz kalkulacyjny*). Powstanie 5 zakładek.
2. **Twoje adresy testowe.** W zakładce `Magazyn` zamień `email_dostawcy` na aliasy własnej skrzynki, np.
   `twoj.mail+nutripol@gmail.com`. Maile „do dostawców” trafią wtedy do Ciebie.
3. **Slack.** Darmowa przestrzeń robocza i kanał `#zamowienia`.
4. **Data store w Make.** *Data stores › Add data store*: nazwa `vf_zamowienia`, nowa struktura danych `vf_zamowienie`
   z polami `nr` (Text), `status` (Text), `data` (Date). Klucz rekordu = ID zamówienia z Shopify.
   To pamięć scenariusza: chroni przed podwójną realizacją, gdy Shopify ponowi webhook.
5. **Python** (do symulatora): `pip install -r requirements.txt`.

---

## Scenariusz 02 · Mock API (Fakturownia + InPost) – 5 min

Budujesz go pierwszy, bo scenariusz 01 z niego korzysta. Udaje dwa zewnętrzne API i odpowiada w ich formacie.
Na produkcji podmieniasz tylko adresy w module 2 scenariusza 01, a reszta zostaje bez zmian.

1. *Create a new scenario* › menu `…` › **Import blueprint** › `make/blueprints/02-mock-api.blueprint.json`.
2. Kliknij moduł 1 (webhook) › *Add* › nazwa `vitaforge-mock-api` › skopiuj adres.
3. Włącz scenariusz (*Scheduling* ON, „Immediately”).
4. Test w przeglądarce lub terminalu:
   ```bash
   curl -X POST "ADRES_WEBHOOKA?mock=invoice" -H "Content-Type: application/json" -d "{\"invoice\":{\"buyer_name\":\"Test\",\"oid\":\"#1\"}}"
   ```
   Odpowiedź: JSON z numerem `FV/2026/11/…` i `view_url`. Dla `?mock=shipment` dostaniesz `tracking_number`.

> Jeśli import zgłosi błąd, zbuduj go ręcznie: **Webhooks › Custom webhook** → **Tools › Set multiple variables**
> (`doc_id` = `{{floor(random * 900000) + 100000}}`, `tracking` = `65{{formatDate(now; "YYMMDDHHmmssSSS")}}{{floor(random * 9000000) + 1000000}}`)
> → **Router** z 3 trasami → na każdej **Webhooks › Webhook response** (status 201, nagłówek `Content-Type: application/json`,
> treść jak w blueprincie). Filtry tras: `{{1.mock}}` równe `invoice` / równe `shipment` / pozostałe → status 400.

---

## Scenariusz 01 · Przyjęcie i realizacja zamówienia (główny)

```
1 Webhook ─ 2 Dane ─ 3 Walidacja i ryzyko ─ 4 Czy już przetworzone? ─ 5 Router
   ├─ A Duplikat ............ 6 Log błędu
   ├─ B Błędne dane ......... 7 Log błędu ─ 8 Mail do obsługi ─ 9 Zapis statusu
   ├─ C Do weryfikacji ...... 10 Arkusz weryfikacji ─ 11 Slack ─ 12 Zapis statusu
   └─ D Realizacja .......... 13 Iterator pozycji ─ 14 Stan magazynu ─ 15 Pozycja ─ 16 Agregator ─ 17 Podsumowanie ─ 18 Router
          ├─ D1 Brak towaru ... 19 Log ─ 20 Mail do klienta ─ 21 Slack ─ 22 Zapis statusu
          └─ D2 Wysyłka ....... 23 Faktura ─ 24 Przesyłka ─ 25 Potwierdzenie ─ 26 Log zamówienia ─ 27 Zapis statusu ─ 28 Iterator ─ 29 Zdejmij ze stanu
```

**Ustawienia scenariusza** (ikona koła zębatego na dole):
- **Sequential processing: ON**. Zamówienia przetwarzane są po kolei, więc dwa równoczesne nie sprzedadzą tej samej ostatniej sztuki.
- **Allow storing of incomplete executions: ON**. Gdy API faktur nie odpowie, wykonanie czeka na ponowienie, zamiast przepaść.

### 1 · Webhooks › Custom webhook – „Nowe zamówienie (Shopify)”
- *Add* › nazwa `vitaforge-orders`. Skopiuj adres i zapisz go w zmiennej `MAKE_ORDERS_WEBHOOK`.
- Kliknij *Redetermine data structure* i wyślij jedno zamówienie:
  ```bash
  python simulator/send_orders.py --scenario ok --url ADRES_WEBHOOKA
  ```
  Make zapamięta strukturę Shopify (`line_items`, `shipping_address` itd.).
- Brak modułu *Webhook response* jest celowy: Make od razu odpowiada `200 Accepted`, a Shopify wymaga odpowiedzi w ciągu 5 s.

### 2 · Tools › Set multiple variables – „Dane”
| Zmienna | Wartość |
|---|---|
| `api_faktury` | `ADRES_MOCK_API?mock=invoice` (produkcja: `https://TWOJA-FIRMA.fakturownia.pl/invoices.json`) |
| `api_wysylki` | `ADRES_MOCK_API?mock=shipment` (produkcja: `https://api-shipx-pl.easypack24.net/v1/organizations/ID/shipments`) |
| `email_obslugi` | Twój adres |
| `email` | `{{lower(trim(1.email))}}` |
| `domena` | `{{last(split(lower(trim(1.email)); "@"))}}` |
| `wartosc` | `{{parseNumber(1.total_price; ".")}}` |
| `klient` | `{{1.shipping_address.first_name}} {{1.shipping_address.last_name}}` |
| `telefon` | `{{replace(replace(1.shipping_address.phone; /\D/g; emptystring); /^48(\d{9})$/; "$1")}}` |
| `dostawa` | `{{first(map(1.shipping_lines; "code"))}}` |
| `paczkomat` | `{{first(map(1.note_attributes; "value"; "name"; "paczkomat"))}}` |
| `max_ilosc` | `{{max(map(1.line_items; "quantity"))}}` |
| `nowy_klient` | `{{if(1.customer.orders_count <= 1; 1; 0)}}` |

Adresy API trzymasz w jednym miejscu, więc przejście z mocka na produkcję to zmiana dwóch pól.

### 3 · Tools › Set multiple variables – „Walidacja i ryzyko”
Reguły są opisane w [`reguly-biznesowe.md`](reguly-biznesowe.md) i zapisane 1:1 w `simulator/rules.py`.

**`bledy`** (pusty tekst = brak błędów):
```
{{if(ifempty(2.email; "#") = "#"; "brak e-maila; "; if(length(replace(2.email; /^[^@\s]+@[^@\s]+\.[a-z]{2,}$/; emptystring)) > 0; "nieprawidłowy e-mail; "; emptystring))}}{{if(length(replace(ifempty(1.shipping_address.zip; "#"); /^\d{2}-\d{3}$/; emptystring)) > 0; "nieprawidłowy kod pocztowy; "; emptystring)}}{{if(length(2.telefon) != 9; "nieprawidłowy telefon; "; emptystring)}}{{if(length(1.line_items) = 0; "brak pozycji; "; emptystring)}}{{if(2.dostawa = "inpost_locker" & ifempty(2.paczkomat; "#") = "#"; "brak paczkomatu; "; emptystring)}}
```

**`ryzyko_pkt`**:
```
{{if(2.wartosc > 1500; 30; 0) + if(2.nowy_klient = 1 & 2.wartosc > 600; 15; 0) + if(contains(split("mailinator.com,yopmail.com,10minutemail.com,guerrillamail.com,tempmail.com,trashmail.com"; ","); 2.domena); 30; 0) + if(lower(1.billing_address.city) != lower(1.shipping_address.city); 25; 0) + if(2.max_ilosc >= 10; 20; 0) + if(1.gateway = "cash_on_delivery" & 2.wartosc > 800; 15; 0)}}
```

**`powody_ryzyka`**:
```
{{if(2.wartosc > 1500; "wysoka wartość; "; emptystring)}}{{if(2.nowy_klient = 1 & 2.wartosc > 600; "nowy klient z dużym koszykiem; "; emptystring)}}{{if(contains(split("mailinator.com,yopmail.com,10minutemail.com,guerrillamail.com,tempmail.com,trashmail.com"; ","); 2.domena); "jednorazowy e-mail; "; emptystring)}}{{if(lower(1.billing_address.city) != lower(1.shipping_address.city); "różne miasto faktury i dostawy; "; emptystring)}}{{if(2.max_ilosc >= 10; "duża ilość jednego produktu; "; emptystring)}}{{if(1.gateway = "cash_on_delivery" & 2.wartosc > 800; "pobranie przy wysokiej kwocie; "; emptystring)}}
```

> **Wskazówka:** długie formuły wklejaj po jednym bloku `{{…}}` i po każdym klikaj *Run once* z zamówieniem
> `--scenario invalid` lub `--scenario risk`. Gdy Make podkreśli składnię, błąd jest w ostatnio dodanym bloku.

### 4 · Data store › Check the existence of a record – „Czy już przetworzone?”
Data store `vf_zamowienia`, Key: `{{1.id}}`. Wynik: pole *Exists* (prawda/fałsz).

### 5 · Router + filtry tras
Filtr ustawiasz, klikając w kropki na linii między routerem a pierwszym modułem trasy.

| Trasa | Nazwa filtra | Warunki (wszystkie muszą być spełnione) |
|---|---|---|
| A | Duplikat | `{{4.exist}}` · *Boolean: Equal to* · `true` |
| B | Błędne dane | `{{4.exist}}` = `false` **i** `{{length(3.bledy)}}` · *Numeric: Greater than* · `0` |
| C | Do weryfikacji | `{{4.exist}}` = `false` **i** `{{length(3.bledy)}}` = `0` **i** `{{3.ryzyko_pkt}}` · *Numeric: Greater than or equal to* · `50` |
| D | Realizacja | `{{4.exist}}` = `false` **i** `{{length(3.bledy)}}` = `0` **i** `{{3.ryzyko_pkt}}` · *Numeric: Less than* · `50` |

Trasy wzajemnie się wykluczają, więc każde zamówienie trafia dokładnie do jednej.

### Trasa A – Duplikat
**6 · Google Sheets › Add a row** – zakładka `Błędy`: `data` = `{{formatDate(now; "YYYY-MM-DD HH:mm")}}`, `nr` = `{{1.name}}`,
`shopify_id` = `{{1.id}}`, `typ` = `duplikat`, `opis` = `Ponowna dostawa webhooka – zignorowano`, `email` = `{{2.email}}`.

### Trasa B – Błędne dane
**7 · Google Sheets › Add a row** – `Błędy`: jak w 6, ale `typ` = `błędne dane`, `opis` = `{{3.bledy}}`.

**8 · Gmail › Send an email** – do `{{2.email_obslugi}}`
- Temat: `⚠️ Zamówienie {{1.name}} wymaga poprawy danych`
- Treść (HTML): `Zamówienie {{1.name}} ({{2.klient}}, {{1.total_price}} zł) zatrzymane. Problemy: <b>{{3.bledy}}</b><br>Skontaktuj się z klientem: {{1.email}}, {{1.shipping_address.phone}}`

**9 · Data store › Add/replace a record** – Key `{{1.id}}`, `nr` = `{{1.name}}`, `status` = `błąd danych`, `data` = `{{now}}`.

### Trasa C – Do weryfikacji
**10 · Google Sheets › Add a row** – `Do weryfikacji`: `data`, `nr`, `shopify_id`, `klient` = `{{2.klient}}`, `email` = `{{2.email}}`,
`wartosc` = `{{2.wartosc}}`, `ryzyko_pkt` = `{{3.ryzyko_pkt}}`, `powody` = `{{3.powody_ryzyka}}`. Kolumnę `decyzja` zostaw pustą (wybiera człowiek).

**11 · Slack › Create a message** – kanał `#zamowienia`:
```
:rotating_light: *Zamówienie {{1.name}} wstrzymane do weryfikacji* ({{3.ryzyko_pkt}} pkt)
Klient: {{2.klient}} · {{1.total_price}} zł · {{1.gateway}}
Powody: {{3.powody_ryzyka}}
Decyzja w arkuszu „Do weryfikacji”.
```

**12 · Data store › Add/replace a record** – `status` = `wstrzymane`.

### Trasa D – Realizacja
**13 · Flow Control › Iterator** – Array: `{{1.line_items}}`. Każda pozycja koszyka idzie dalej osobno.

**14 · Google Sheets › Search rows** – „Stan magazynu”. Zakładka `Magazyn`, filtr: `sku` *Equal to* `{{13.sku}}`, Limit `1`.

**15 · Tools › Set multiple variables** – „Pozycja”:
| Zmienna | Wartość |
|---|---|
| `brak` | `{{if(14.stan < 13.quantity; 1; 0)}}` |
| `pozycja_txt` | `{{13.quantity}}× {{13.title}}` |
| `pozycja_json` | `{"name": "{{13.title}}", "quantity": {{13.quantity}}, "total_price_gross": {{parseNumber(13.price; ".") * 13.quantity}}, "tax": {{14.vat}}}` |

**16 · Flow Control › Array aggregator** – Source module: **13 (Iterator)**. Zaznacz pola: z 13 `sku`, `title`, `quantity`;
z 14 `stan`, `Row number`; z 15 `brak`, `pozycja_txt`, `pozycja_json`. Pozycje wracają do jednej paczki danych.

**17 · Tools › Set multiple variables** – „Podsumowanie koszyka”:
| Zmienna | Wartość |
|---|---|
| `liczba_brakow` | `{{sum(map(16.array; "brak")) + length(1.line_items) - length(16.array)}}` |
| `lista_brakow` | `{{join(map(16.array; "title"; "brak"; "1"); ", ")}}` |
| `pozycje` | `{{join(map(16.array; "pozycja_txt"); ", ")}}` |

Druga część `liczba_brakow` łapie SKU, którego nie ma w arkuszu: wyszukiwanie zwraca 0 wierszy,
więc pozycja „znika” z agregatora. Bez tego zamówienie z nieznanym produktem poszłoby do wysyłki.

**18 · Router** – D1: `{{17.liczba_brakow}}` *Greater than* `0`; D2: `{{17.liczba_brakow}}` *Equal to* `0`.

#### D1 – Brak towaru
**19 · Google Sheets › Add a row** – `Błędy`: `typ` = `brak towaru`, `opis` = `Brak: {{17.lista_brakow}}{{if(length(1.line_items) > length(16.array); " + nieznane SKU"; emptystring)}}`.

**20 · Gmail › Send an email** – do `{{2.email}}`
- Temat: `Twoje zamówienie {{1.name}} – krótkie opóźnienie`
- Treść: `Dzień dobry {{1.shipping_address.first_name}}, dziękujemy za zamówienie! Produkt {{17.lista_brakow}} chwilowo jest niedostępny. Skontaktujemy się w ciągu 24 h z propozycją: wysyłka po dostawie, zamiennik albo zwrot środków. Zespół VitaForge`

**21 · Slack › Create a message**: `:package: {{1.name}} czeka na towar: {{17.lista_brakow}} · klient {{2.klient}}, {{1.total_price}} zł`

**22 · Data store › Add/replace a record** – `status` = `oczekuje na towar`.

#### D2 – Wysyłka
**23 · HTTP › Make a request** – „Wystaw fakturę (Fakturownia)”
- URL `{{2.api_faktury}}`, Method `POST`, Body type `Raw`, Content type `JSON (application/json)`, **Parse response: Yes**
- Request content:
```json
{
  "api_token": "DEMO_TOKEN",
  "invoice": {
    "kind": "vat",
    "sell_date": "{{formatDate(now; "YYYY-MM-DD")}}",
    "issue_date": "{{formatDate(now; "YYYY-MM-DD")}}",
    "payment_type": "{{if(1.gateway = "cash_on_delivery"; "cod"; "transfer")}}",
    "status": "{{if(1.financial_status = "paid"; "paid"; "issued")}}",
    "buyer_name": "{{2.klient}}",
    "buyer_email": "{{2.email}}",
    "buyer_street": "{{1.billing_address.address1}}",
    "buyer_post_code": "{{1.billing_address.zip}}",
    "buyer_city": "{{1.billing_address.city}}",
    "buyer_country": "PL",
    "oid": "{{1.name}}",
    "positions": [{{join(map(16.array; "pozycja_json"); ",")}}]
  }
}
```
- **Error handler** (prawy klik › *Add error handler*) › **Break**: Number of attempts `3`, Interval `5` min.

**24 · HTTP › Make a request** – „Utwórz przesyłkę (InPost ShipX)”, ustawienia jak w 23, URL `{{2.api_wysylki}}`
(produkcja: dodaj nagłówek `Authorization: Bearer TOKEN`):
```json
{
  "receiver": {
    "name": "{{2.klient}}",
    "first_name": "{{1.shipping_address.first_name}}",
    "last_name": "{{1.shipping_address.last_name}}",
    "email": "{{2.email}}",
    "phone": "{{2.telefon}}",
    "address": {
      "street": "{{1.shipping_address.address1}}",
      "city": "{{1.shipping_address.city}}",
      "post_code": "{{1.shipping_address.zip}}",
      "country_code": "PL"
    }
  },
  "parcels": {"template": "small"},
  "custom_attributes": {"target_point": "{{2.paczkomat}}", "sending_method": "dispatch_order"},
  "service": "{{if(2.dostawa = "inpost_locker"; "inpost_locker_standard"; "inpost_courier_standard")}}",
  "reference": "{{1.name}}"
}
```
Error handler **Break** jak wyżej.

**25 · Gmail › Send an email** – „Potwierdzenie dla klienta”, do `{{2.email}}`
- Temat: `Zamówienie {{1.name}} przyjęte do realizacji ✅`
- Treść (HTML):
```html
<p>Dzień dobry {{1.shipping_address.first_name}},</p>
<p>dziękujemy za zakupy w VitaForge! Twoje zamówienie <b>{{1.name}}</b> jest już pakowane.</p>
<p><b>Produkty:</b> {{17.pozycje}}<br>
<b>Kwota:</b> {{1.total_price}} zł<br>
<b>Faktura:</b> <a href="{{23.data.view_url}}">{{23.data.number}}</a><br>
<b>Śledzenie przesyłki:</b> <a href="https://inpost.pl/sledzenie-przesylek?number={{24.data.tracking_number}}">{{24.data.tracking_number}}</a></p>
<p>Zespół VitaForge</p>
```

**26 · Google Sheets › Add a row** – `Zamówienia`:
`data` = `{{formatDate(1.created_at; "YYYY-MM-DD HH:mm")}}`, `nr` = `{{1.name}}`, `shopify_id` = `{{1.id}}`, `klient` = `{{2.klient}}`,
`email` = `{{2.email}}`, `wartosc` = `{{2.wartosc}}`, `platnosc` = `{{1.gateway}}`, `dostawa` = `{{2.dostawa}}`, `pozycje` = `{{17.pozycje}}`,
`ryzyko_pkt` = `{{3.ryzyko_pkt}}`, `status` = `wysłane do realizacji`, `nr_faktury` = `{{23.data.number}}`, `link_faktury` = `{{23.data.view_url}}`,
`nr_przesylki` = `{{24.data.tracking_number}}`, `link_sledzenia` = `https://inpost.pl/sledzenie-przesylek?number={{24.data.tracking_number}}`.

**27 · Data store › Add/replace a record** – `status` = `zrealizowane`.

**28 · Flow Control › Iterator** – Array: `{{16.array}}`.

**29 · Google Sheets › Update a row** – „Zdejmij ze stanu”. Zakładka `Magazyn`, Row number `{{28.__ROW_NUMBER__}}`
(w panelu mapowania: *Row number* z modułu 28), `stan` = `{{28.stan - 28.quantity}}`,
`ostatnia_zmiana` = `{{formatDate(now; "YYYY-MM-DD HH:mm")}} · {{1.name}}`. **Pozostałe kolumny zostaw puste**:
Make ich nie nadpisze, a kolumna `do_zamowienia` ma formułę.

Stan zdejmujesz na końcu, gdy faktura i przesyłka już istnieją. Jeśli API padnie, magazyn się nie rozjedzie.

---

## Scenariusz 03 · Niskie stany → zamówienie do dostawcy

Harmonogram: codziennie o 8:00 (*Scheduling › Every day*).

**1 · Google Sheets › Search rows** – `Magazyn`, filtr `do_zamowienia` *Equal to* `TAK`.
Kolumna `do_zamowienia` to formuła w arkuszu (`stan <= prog_minimalny` i jeszcze nie zamówiono), bo filtr
Google Sheets w Make porównuje kolumnę ze stałą wartością, a nie z inną kolumną.

**2 · Google Sheets › Update a row** – Row number `{{1.__ROW_NUMBER__}}`, `status_zamowienia` = `zamówione`,
`data_zamowienia` = `{{formatDate(now; "YYYY-MM-DD")}}`. Dzięki temu jutro nie zamówisz tego samego drugi raz.

**3 · Tools › Text aggregator** – Source module `1`, **Group by** `{{1.dostawca}}|{{1.email_dostawcy}}`, Row separator: brak, Text:
```html
<tr><td>{{1.sku}}</td><td>{{1.nazwa}}</td><td style="text-align:right">{{1.stan}}</td><td style="text-align:right"><b>{{1.ilosc_zamawiana}}</b></td></tr>
```
Wynik: jedna paczka danych na dostawcę, więc każdy dostaje jeden mail ze wszystkimi swoimi pozycjami.

**4 · Gmail › Send an email** – do `{{last(split(3.key; "|"))}}`
- Temat: `Zamówienie VitaForge – {{formatDate(now; "DD.MM.YYYY")}}`
- Treść:
```html
<p>Dzień dobry,</p><p>prosimy o realizację zamówienia i potwierdzenie terminu dostawy:</p>
<table border="1" cellpadding="6" style="border-collapse:collapse">
<tr><th>SKU</th><th>Produkt</th><th>Obecny stan</th><th>Zamawiana ilość</th></tr>
{{3.text}}
</table><p>Pozdrawiamy,<br>Dział zakupów VitaForge</p>
```

**5 · Google Sheets › Add a row** – `Zamówienia do dostawców`: `data` = `{{formatDate(now; "YYYY-MM-DD")}}`,
`dostawca` = `{{first(split(3.key; "|"))}}`, `email` = `{{last(split(3.key; "|"))}}`,
`liczba_pozycji` = `{{length(split(3.text; "</tr>")) - 1}}`, `pozycje` = `{{replace(replace(3.text; /<\/td><td[^>]*>/g; " | "); /<[^>]+>/g; " ")}}`.

**6 · Slack › Create a message**: `:truck: Wysłano zamówienie do *{{first(split(3.key; "|"))}}* ({{length(split(3.text; "</tr>")) - 1}} poz.)`

Po dostawie towaru wpisujesz nowy `stan` i czyścisz `status_zamowienia`. Rozszerzenie: scenariusz „Przyjęcie dostawy” z formularza.

---

## Obsługa błędów – podsumowanie

| Miejsce | Mechanizm | Po co |
|---|---|---|
| Webhook | Data store + trasa A | Shopify ponawia webhooki: to samo zamówienie nie zostanie zafakturowane dwa razy |
| Ustawienia scenariusza 01 | Sequential processing | brak wyścigu o ostatnią sztukę towaru |
| HTTP faktura / przesyłka | Break, 3 próby co 5 min + incomplete executions | chwilowa awaria API nie gubi zamówienia |
| Kolejność modułów | stan zdejmowany na końcu | awaria w środku nie psuje magazynu |
| Moduł 17 | porównanie liczby pozycji | nieznane SKU nie trafi do wysyłki |
| Scenariusz 03 | status „zamówione” | brak podwójnych zamówień u dostawcy |
| Cały scenariusz | *Notify on error* w ustawieniach konta | wiesz o problemie zanim zgłosi go klient |

## Zużycie operacji

Zamówienie z 2 pozycjami na trasie D2 to ok. 20 operacji w scenariuszu 01 i 4 w Mock API. Trasy A–C to 5–9 operacji.
Test `--scenario mix --count 20` zużywa ok. 350–400 operacji. Sprawdź limit swojego planu w Make,
zanim puścisz większą serię.
