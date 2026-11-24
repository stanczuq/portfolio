"""
Uruchamia cały pipeline od surowych danych do raportu:

  1. generate_data   – (tylko demo) generuje surowy eksport zamówień i wydatków reklamowych
  2. clean_data      – czyści dane i zapisuje raport jakości danych
  3. build_dashboard – buduje interaktywny dashboard (dashboard/index.html)
  4. build_report    – generuje raport tygodniowy PDF + e-mail + podsumowanie JSON
  5. notify          – przekazuje raport do Make (dry run bez MAKE_WEBHOOK_URL)

Użycie:
  python run_all.py                 # pełny przebieg na danych demo
  python run_all.py --skip-generate # na istniejących danych w data/raw (np. prawdziwy eksport)
  python run_all.py --week 2026-W46 # raport za konkretny tydzień
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import build_dashboard  # noqa: E402
import build_report  # noqa: E402
import clean_data  # noqa: E402
import generate_data  # noqa: E402
import notify  # noqa: E402


def step(name, fn, *a):
    t = time.perf_counter()
    print(f"\n▶ {name}")
    out = fn(*a)
    print(f"  ✓ {time.perf_counter() - t:.1f} s")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-generate", action="store_true")
    ap.add_argument("--week")
    ap.add_argument("--dashboard-url", default="https://example.com/dashboard")
    a = ap.parse_args()
    if not a.skip_generate:
        step("Generowanie danych demo", generate_data.main)
    step("Czyszczenie danych", clean_data.main)
    step("Budowa dashboardu", build_dashboard.main)
    step("Raport tygodniowy", build_report.main, a.week, a.dashboard_url)
    step("Powiadomienie (Make)", notify.main, a.week)
