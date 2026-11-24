"""Narzędzia „sklepowe”: zamówienia, katalog i stany magazynowe.

W demo dane są w plikach `data/`. U klienta te same funkcje odpytują Shopify Admin API
(zamówienia) i arkusz `Magazyn` z projektu „Automatyzacja zamówień w Make” (stany).
Wszystkie narzędzia są TYLKO DO ODCZYTU: asystent niczego nie anuluje, nie zwraca pieniędzy i nie zmienia adresu.
"""
import csv
import json
from dataclasses import dataclass
from pathlib import Path

from .text import tokens

DELIVERY_NAMES = {
    "inpost_locker": "InPost Paczkomat 24/7",
    "inpost_courier": "Kurier InPost",
    "dpd_cod": "Kurier DPD (pobranie)",
}


@dataclass
class Product:
    sku: str
    name: str
    category: str
    price: float
    stock: int
    restock_date: str | None

    @property
    def available(self) -> bool:
        return self.stock > 0


class Store:
    def __init__(self, data_dir: Path):
        data_dir = Path(data_dir)
        stock = {r["sku"]: r for r in csv.DictReader(open(data_dir / "stock.csv", encoding="utf-8"))}
        self.products: dict[str, Product] = {}
        for r in csv.DictReader(open(data_dir / "products.csv", encoding="utf-8")):
            s = stock.get(r["sku"], {})
            self.products[r["sku"]] = Product(
                r["sku"], r["product_name"], r["category"], float(r["unit_price"]),
                int(s.get("stan") or 0), s.get("dostawa_planowana") or None,
            )
        self.orders = {o["numer"]: o for o in json.load(open(data_dir / "orders.json", encoding="utf-8"))}
        self._name_tokens = {sku: set(tokens(p.name)) for sku, p in self.products.items()}

    # --- zamówienia -----------------------------------------------------------
    def lookup_order(self, number: str | None, sender_email: str | None) -> dict:
        """Zwraca status wyszukiwania i dane zamówienia tylko po weryfikacji adresu e-mail."""
        if not number:
            return {"status": "brak_numeru"}
        order = self.orders.get(number)
        if not order:
            return {"status": "nie_znaleziono", "numer": number}
        if not sender_email or sender_email.lower() != order["email"].lower():
            return {"status": "email_niezgodny", "numer": number}
        return {"status": "znaleziono", "zamowienie": self._describe(order)}

    def _describe(self, o: dict) -> dict:
        items = []
        for p in o["pozycje"]:
            prod = self.products.get(p["sku"])
            items.append({
                "produkt": prod.name if prod else p["sku"], "ilosc": p["ilosc"],
                "brak": bool(prod and prod.stock < p["ilosc"]),
                "dostawa_planowana": prod.restock_date if prod else None,
            })
        return {**o, "metoda_dostawy": DELIVERY_NAMES.get(o["metoda_dostawy"], o["metoda_dostawy"]), "pozycje": items}

    # --- produkty ---------------------------------------------------------------
    def find_products(self, text: str, limit: int = 3) -> list[Product]:
        """Dopasowanie nazw produktów do treści wiadomości (z uwzględnieniem odmiany i gramatury)."""
        msg = set(tokens(text))
        scored = []
        for sku, name_toks in self._name_tokens.items():
            head = tokens(self.products[sku].name)[0]       # główne słowo nazwy: „kreat”, „bialk”…
            if head not in msg and sku.lower() not in text.lower():
                continue
            scored.append((len(name_toks & msg) + (5 if sku.lower() in text.lower() else 0), sku))
        if not scored:
            return []
        best = max(s for s, _ in scored)
        return [self.products[sku] for s, sku in sorted(scored, key=lambda x: -x[0]) if s == best][:limit]
