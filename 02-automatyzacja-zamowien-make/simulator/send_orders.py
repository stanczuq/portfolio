"""Symulator zamówień sklepu VitaForge w formacie webhooka Shopify `orders/create`.

Wysyła zamówienia testowe do webhooka Make (scenariusz 1 „Przyjęcie zamówienia”),
w tym celowo błędne, podejrzane, z brakującym towarem i zduplikowane. Dla każdego
zamówienia zapisuje trasę, którą POWINIEN wybrać Make, żeby dało się sprawdzić wynik.

Przykłady:
    python simulator/send_orders.py                       # dry run: 12 zamówień (mix) do samples/
    python simulator/send_orders.py --scenario risk       # jedno podejrzane zamówienie
    python simulator/send_orders.py --scenario mix --count 20 \
        --url https://hook.eu2.make.com/xxxx --inbox twoj.mail@gmail.com

Zamiast flag możesz wpisać MAKE_ORDERS_WEBHOOK i TEST_INBOX do pliku .env (wzór: .env.example).
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import os

try:  # adres webhooka i skrzynkę można trzymać w pliku .env
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from catalog import load_products
from rules import expected_route, risk, validation_errors

ROOT = Path(__file__).resolve().parents[1]
TZ = timezone(timedelta(hours=1))
SCENARIOS = ["ok", "invalid", "risk", "stockout", "duplicate"]
MIX_WEIGHTS = {"ok": 70, "invalid": 10, "risk": 10, "stockout": 5, "duplicate": 5}

FEMALE = ["Anna", "Katarzyna", "Magdalena", "Agnieszka", "Natalia", "Ewa", "Julia", "Aleksandra"]
MALE = ["Piotr", "Tomasz", "Michał", "Jakub", "Kamil", "Bartosz", "Mateusz", "Paweł"]
LAST = ["Nowak", "Kowalski", "Wiśniewski", "Wójcik", "Kamiński", "Lewandowski",
        "Zieliński", "Szymański", "Woźniak", "Dąbrowski", "Kozłowski", "Mazur"]
CITIES = [("Warszawa", "00-950", "WAW01M"), ("Kraków", "30-001", "KRA12A"),
          ("Wrocław", "50-001", "WRO05N"), ("Poznań", "60-101", "POZ33M"),
          ("Gdańsk", "80-001", "GDA08M"), ("Łódź", "90-001", "LOD21A"),
          ("Lublin", "20-001", "LUB04M"), ("Białystok", "15-001", "BIA02N")]
STREETS = ["ul. Długa", "ul. Polna", "ul. Leśna", "ul. Słoneczna", "ul. Kwiatowa", "al. Jana Pawła II"]


class OrderFactory:
    def __init__(self, inbox: str | None, seed: int | None):
        self.rng = random.Random(seed)
        self.products = load_products()
        self.by_sku = {p["sku"]: p for p in self.products}
        self.inbox = inbox
        self.base_id = int(time.time() * 1000) * 10
        self.n = 0

    # --- pomocnicze -----------------------------------------------------
    def _email(self, first: str, last: str, order_no: int) -> str:
        if self.inbox and "@" in self.inbox:  # aliasy plus: wszystkie maile trafią do Twojej skrzynki
            user, domain = self.inbox.split("@", 1)
            return f"{user}+vf{order_no}@{domain}"
        plain = (first + "." + last).lower().translate(str.maketrans("ąćęłńóśźż", "acelnoszz"))
        return f"{plain}@example.com"

    def _address(self, first, last, city):
        name, zip_code, _ = city
        phone = f"+48 5{self.rng.randint(10, 99)} {self.rng.randint(100, 999)} {self.rng.randint(100, 999)}"
        return {"first_name": first, "last_name": last, "address1": f"{self.rng.choice(STREETS)} {self.rng.randint(1, 120)}",
                "city": name, "zip": zip_code, "country_code": "PL", "phone": phone}

    def _line(self, sku: str, qty: int) -> dict:
        p = self.by_sku[sku]
        return {"id": self.base_id + self.rng.randint(1, 10**6), "sku": sku, "title": p["product_name"],
                "quantity": qty, "price": f"{p['unit_price']:.2f}"}

    # --- zamówienie bazowe (poprawne, niskie ryzyko) ------------------------
    def base(self) -> dict:
        self.n += 1
        oid = self.base_id + self.n
        order_no = 10000 + (self.base_id // 10 + self.n) % 90000
        female = self.rng.random() < 0.5
        first, last = self.rng.choice(FEMALE if female else MALE), self.rng.choice(LAST)
        if female and last.endswith("ki"):
            last = last[:-1] + "a"
        city = self.rng.choice(CITIES)
        addr = self._address(first, last, city)
        skus = [p["sku"] for p in self.products if p["sku"] != "KRE-500"]
        lines = [self._line(s, self.rng.choice([1, 1, 1, 2, 3])) for s in self.rng.sample(skus, self.rng.choice([1, 2, 2, 3]))]
        locker = self.rng.random() < 0.65
        shipping = 0.0 if self._subtotal(lines) >= 199 else (12.99 if locker else 16.99)
        gateway = self.rng.choice(["przelewy24", "blik", "przelewy24", "cash_on_delivery"])
        created = datetime.now(TZ).replace(microsecond=0)
        order = {
            "id": oid, "name": f"#{order_no}", "order_number": order_no,
            "email": self._email(first, last, order_no), "phone": addr["phone"],
            "created_at": created.isoformat(), "currency": "PLN",
            "financial_status": "pending" if gateway == "cash_on_delivery" else "paid",
            "gateway": gateway, "source_name": "web",
            "customer": {"id": 7_000_000_000 + self.rng.randint(1, 99999), "first_name": first, "last_name": last,
                         "email": None, "orders_count": self.rng.choice([1, 2, 3, 5, 8])},
            "billing_address": copy.deepcopy(addr), "shipping_address": addr,
            "line_items": lines,
            "shipping_lines": [{"title": "InPost Paczkomat 24/7" if locker else "Kurier InPost",
                                "code": "inpost_locker" if locker else "inpost_courier", "price": f"{shipping:.2f}"}],
            "note_attributes": [{"name": "paczkomat", "value": city[2]}] if locker else [],
            "tags": "",
        }
        order["customer"]["email"] = order["email"]
        return self._totals(order)

    @staticmethod
    def _subtotal(lines) -> float:
        return round(sum(float(li["price"]) * li["quantity"] for li in lines), 2)

    def _totals(self, order: dict) -> dict:
        sub = self._subtotal(order["line_items"])
        ship = float(order["shipping_lines"][0]["price"])
        order["subtotal_price"] = f"{sub:.2f}"
        order["total_price"] = f"{sub + ship:.2f}"
        return order

    # --- warianty --------------------------------------------------------
    def make(self, scenario: str) -> tuple[dict, str]:
        o = self.base()
        if scenario == "ok":
            return o, "poprawne zamówienie"
        if scenario == "invalid":
            kind = self.rng.choice(["email", "zip", "phone", "locker"])
            if kind == "email":
                o["email"] = o["email"].replace("@", "").replace(".com", "")  # brak @
                o["customer"]["email"] = o["email"]
            elif kind == "zip":
                o["shipping_address"]["zip"] = o["shipping_address"]["zip"].replace("-", "")
            elif kind == "phone":
                o["shipping_address"]["phone"] = "+48 51 234"
            else:
                o["shipping_lines"][0].update(code="inpost_locker", title="InPost Paczkomat 24/7")
                o["note_attributes"] = []
            return o, f"błędne dane ({kind})"
        if scenario == "risk":
            o["customer"]["orders_count"] = 1
            o["email"] = o["customer"]["email"] = f"zakupy{o['order_number']}@mailinator.com"
            o["line_items"] = [self._line("WHY-2K", 4), self._line("CIT-300", 12)]
            other = self.rng.choice([c for c in CITIES if c[0] != o["shipping_address"]["city"]])
            o["billing_address"].update(city=other[0], zip=other[1])
            o["gateway"], o["financial_status"] = "cash_on_delivery", "pending"
            o["shipping_lines"][0]["price"] = "0.00"
            return self._totals(o), "podejrzane: nowy klient, jednorazowy e-mail, 12 szt., inne miasto, pobranie"
        if scenario == "stockout":
            o["line_items"] = [self._line("KRE-500", 2), self._line("SHK-700", 1)]
            return self._totals(o), "zawiera wyprzedany produkt KRE-500"
        raise ValueError(scenario)


def post(url: str, order: dict) -> str:
    import requests
    r = requests.post(url, json=order, timeout=15, headers={
        "X-Shopify-Topic": "orders/create", "X-Shopify-Shop-Domain": "vitaforge-demo.myshopify.com"})
    return f"{r.status_code} {r.text.strip()[:40]}"


def load_env_file() -> None:
    """Wczytuje zmienne z pliku .env w katalogu projektu (bez dodatkowych bibliotek)."""
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main(argv=None) -> int:
    load_env_file()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", choices=SCENARIOS + ["mix"], default="mix")
    ap.add_argument("--count", type=int, default=None, help="liczba zamówień (domyślnie 1, dla mix 12)")
    ap.add_argument("--url", default=os.getenv("MAKE_ORDERS_WEBHOOK"), help="adres webhooka Make; brak = dry run")
    ap.add_argument("--inbox", default=os.getenv("TEST_INBOX"), help="Twój e-mail: klienci dostaną aliasy twoj+vf123@...")
    ap.add_argument("--delay", type=float, default=3.0, help="sekundy między wysyłkami")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args(argv)

    count = args.count or (12 if args.scenario == "mix" else 1)
    f = OrderFactory(args.inbox, args.seed)
    rng = f.rng
    stock = {p["sku"]: p["stock"] for p in f.products}  # symulowany stan, żeby przewidzieć trasę
    seen: set = set()
    plan: list[tuple[dict, str, str]] = []

    if args.scenario == "mix":
        names = list(MIX_WEIGHTS)
        picks = rng.choices(names, weights=MIX_WEIGHTS.values(), k=count)
        for s in names[1:]:  # każdy typ co najmniej raz, żeby test pokrył wszystkie trasy
            if s not in picks and count >= len(names):
                picks[picks.index("ok")] = s
        rng.shuffle(picks)
    else:
        picks = [args.scenario] * count

    for s in picks:
        if s == "duplicate":
            o, desc = f.make("ok")
            plan += [(o, "duplikat: oryginał", s), (o, "duplikat: ponowna dostawa webhooka", s)]
        else:
            o, desc = f.make(s)
            plan.append((o, desc, s))

    dry = not args.url
    out_dir = ROOT / ("samples" if dry else "runs")
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now(TZ).strftime("%Y%m%d_%H%M%S")
    manifest = out_dir / ("manifest.csv" if dry else f"run_{stamp}.csv")
    if dry:
        for old in out_dir.glob("order_*.json"):
            old.unlink()

    rows = []
    print(f"{'DRY RUN – nic nie jest wysyłane' if dry else 'Wysyłka do ' + args.url[:40] + '…'}\n")
    print(f"{'nr':<8} {'wartość':>9}  {'ryzyko':>6}  {'oczekiwana trasa':<20} opis")
    for i, (o, desc, s) in enumerate(plan, 1):
        route = expected_route(o, stock, seen)
        score, reasons = risk(o)
        if route == "D2: realizacja":
            for li in o["line_items"]:
                stock[li["sku"]] -= li["quantity"]
        seen.add(o["id"])
        status = "-"
        if dry:
            suffix = "_dup" if route.startswith("A") else ""
            (out_dir / f"order_{o['order_number']}{suffix}.json").write_text(
                json.dumps(o, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            status = post(args.url, o)
            if i < len(plan):
                time.sleep(args.delay)
        print(f"{o['name']:<8} {o['total_price']:>9}  {score:>6}  {route:<20} {desc}")
        rows.append({"nr": o["name"], "shopify_id": o["id"], "scenariusz": s, "opis": desc,
                     "wartosc": o["total_price"], "ryzyko_pkt": score, "powody_ryzyka": "; ".join(reasons),
                     "bledy": "; ".join(validation_errors(o)), "oczekiwana_trasa": route, "odpowiedz_make": status})

    with open(manifest, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys(), delimiter=";")
        w.writeheader(); w.writerows(rows)
    print(f"\nZapisano: {manifest.relative_to(ROOT)}")
    low = [k for k, v in stock.items() if v <= f.by_sku[k]["min_level"]]
    print(f"Produkty na/poniżej progu po teście (scenariusz 3 zamówi je u dostawcy): {', '.join(low)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
