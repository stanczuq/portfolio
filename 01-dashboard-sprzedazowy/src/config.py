"""Wspólna konfiguracja projektu: ścieżki, kanały sprzedaży, prowizje, progi alertów."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DASHBOARD_DIR = ROOT / "dashboard"
REPORTS_DIR = ROOT / "reports"

STORE_NAME = "VitaForge"  # fikcyjny sklep demonstracyjny
CURRENCY = "PLN"

# Kanały sprzedaży: prefiks numeru zamówienia -> nazwa kanału
CHANNELS = {
    "WWW": "Sklep WWW",
    "ALG": "Allegro",
    "AMZ": "Amazon.pl",
}
CHANNEL_ORDER = ["Sklep WWW", "Allegro", "Amazon.pl"]

# Koszt sprzedaży w kanale (prowizja marketplace / bramka płatności), % przychodu netto
CHANNEL_FEE = {
    "Sklep WWW": 0.015,
    "Allegro": 0.11,
    "Amazon.pl": 0.15,
}

# Platforma reklamowa -> kanał, do którego przypisujemy koszt (do ROAS)
AD_PLATFORM_CHANNEL = {
    "Meta Ads": "Sklep WWW",
    "Google Ads": "Sklep WWW",
    "Allegro Ads": "Allegro",
    "Amazon Ads": "Amazon.pl",
}

# Progi reguł alertów w raporcie tygodniowym
ALERTS = {
    "channel_revenue_drop_pct": -15.0,   # spadek przychodu kanału t/t ...
    "channel_revenue_drop_min_pln": 2000,  # ... i jednocześnie co najmniej o tyle zł (filtr szumu małych kanałów)
    "return_rate_max_pct": 5.0,          # udział zwróconych zamówień
    "roas_min": 3.0,                     # minimalny akceptowalny ROAS kanału
    "stockout_min_weekly_units": 6,      # produkt sprzedawał >= tyle szt./tydz., a teraz 0
}
