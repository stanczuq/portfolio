"""
Etap 5 pipeline'u: przekazanie raportu do automatyzacji w Make.

Wysyła POST (multipart/form-data) na webhook Make:
  - pola tekstowe z summary_<tydzień>.json (KPI, alerty, gotowy tekst na Slacka),
  - plik PDF raportu i treść e-maila HTML.
Scenariusz Make rozsyła dalej: e-mail z PDF do zarządu, wiadomość na Slacku, zapis KPI w Google Sheets
(opis krok po kroku: automation/make-scenariusz.md).

Adres webhooka czytany jest ze zmiennej środowiskowej MAKE_WEBHOOK_URL.
Bez niej skrypt działa w trybie "dry run" – pokazuje, co zostałoby wysłane.

Użycie:  python src/notify.py [--week 2026-W47]
"""
import argparse
import json
import os
import sys

from config import REPORTS_DIR


def latest_week() -> str:
    weeks = sorted(p.name for p in REPORTS_DIR.iterdir() if p.is_dir())
    if not weeks:
        sys.exit("Brak raportów – uruchom najpierw src/build_report.py")
    return weeks[-1]


def main(week: str | None = None) -> None:
    week = week or latest_week()
    folder = REPORTS_DIR / week
    summary = json.loads((folder / f"summary_{week}.json").read_text(encoding="utf-8"))
    fields = {
        "week": summary["week"],
        "date_from": summary["date_from"],
        "date_to": summary["date_to"],
        "revenue": summary["kpi"]["revenue"],
        "revenue_change_pct": summary["kpi_change_pct"]["revenue"],
        "orders": summary["kpi"]["orders"],
        "roas": summary["kpi"]["roas"],
        "gross_margin_pct": summary["kpi"]["gross_margin_pct"],
        "critical_alerts": summary["critical_alerts"],
        "alerts_json": json.dumps(summary["alerts"], ensure_ascii=False),
        "slack_text": summary["slack_text"],
        "email_html": (folder / f"email_{week}.html").read_text(encoding="utf-8"),
    }
    pdf = folder / f"raport_{week}.pdf"
    url = os.getenv("MAKE_WEBHOOK_URL")

    if not url:
        print("[dry run] Brak MAKE_WEBHOOK_URL – nic nie wysłano. Payload:")
        preview = {k: (v[:120] + "…" if isinstance(v, str) and len(v) > 120 else v) for k, v in fields.items()}
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        print(f"[dry run] Załącznik: {pdf.name} ({pdf.stat().st_size / 1024:.0f} KB)" if pdf.exists() else "[dry run] Brak PDF")
        return

    import requests  # importowane tylko przy faktycznej wysyłce

    files = {"report_pdf": (pdf.name, pdf.open("rb"), "application/pdf")} if pdf.exists() else None
    r = requests.post(url, data={k: str(v) for k, v in fields.items()}, files=files, timeout=60)
    r.raise_for_status()
    print(f"Wysłano raport {week} do Make (HTTP {r.status_code}).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--week")
    main(ap.parse_args().week)
