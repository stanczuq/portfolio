"""Katalog produktów VitaForge (ten sam co w projekcie „Dashboard sprzedażowy”)
oraz startowe stany magazynowe i dostawcy. Z tego pliku powstaje arkusz Google Sheets."""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent

SUPPLIERS = {
    "Białko":             ("NutriPol Hurt",      "dostawca.nutripol@example.com"),
    "Kreatyna":           ("NutriPol Hurt",      "dostawca.nutripol@example.com"),
    "Witaminy i zdrowie": ("VitaLab Sp. z o.o.", "zamowienia.vitalab@example.com"),
    "Przedtreningówki":   ("PowerMix",           "b2b.powermix@example.com"),
    "Akcesoria":          ("GymGear Import",     "orders.gymgear@example.com"),
}

# Stany startowe: celowo kilka produktów blisko progu i jeden wyprzedany (KRE-500),
# żeby od pierwszego testu było widać alerty i zamówienia do dostawców.
START_STOCK = {
    "WHY-900": 85, "WHY-2K": 9, "ISO-700": 40, "VEG-750": 25, "KAZ-700": 18,
    "KRE-500": 0, "KRE-250": 60, "KRE-CAP": 35, "KRE-ALK": 14,
    "VIT-D3K2": 120, "OMG-120": 16, "MAG-B6": 150, "MULTI": 70, "ASHW": 45, "ZINC": 90,
    "PRE-300": 30, "BETA-200": 22, "CIT-300": 12, "CAF-200": 80,
    "SHK-700": 200, "BELT": 8, "GLOV": 30, "BAND": 26, "BOT-1L": 110,
}
MIN_LEVEL = {sku: 15 for sku in START_STOCK} | {
    "WHY-900": 25, "KRE-500": 20, "VIT-D3K2": 30, "MAG-B6": 30, "SHK-700": 40,
    "BELT": 5, "CIT-300": 8, "KRE-ALK": 8,
}
VAT = {"Akcesoria": 23}  # pozostałe kategorie: 8 (przykładowe stawki, do weryfikacji z księgową)


def load_products() -> list[dict]:
    with open(HERE / "products.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["unit_price"] = float(r["unit_price"])
        r["stock"] = START_STOCK[r["sku"]]
        r["min_level"] = MIN_LEVEL[r["sku"]]
        r["reorder_qty"] = max(r["min_level"] * 3, 20)
        r["supplier"], r["supplier_email"] = SUPPLIERS[r["category"]]
        r["vat"] = VAT.get(r["category"], 8)
    return rows
