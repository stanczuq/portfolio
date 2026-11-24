"""
Etap 4 pipeline'u: automatyczny raport tygodniowy.

Dla wskazanego tygodnia ISO (domyślnie ostatni pełny) generuje:
  reports/<tydzień>/raport_<tydzień>.html  – raport do druku (A4)
  reports/<tydzień>/raport_<tydzień>.pdf   – ten sam raport jako PDF (Chrome headless)
  reports/<tydzień>/email_<tydzień>.html   – wersja do wysłania e-mailem (style inline)
  reports/<tydzień>/summary_<tydzień>.json – podsumowanie dla automatyzacji (Make / Slack)

Użycie:  python src/build_report.py [--week 2026-W47]
"""
import argparse
import html
import io
import json
import shutil
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

from config import ALERTS, CHANNEL_ORDER, REPORTS_DIR, STORE_NAME  # noqa: E402
from kpis import WeekSummary, fmt_pct, fmt_pln, load, pct_change, week_summary  # noqa: E402

COLORS = {"Sklep WWW": "#2a78d6", "Allegro": "#eb6834", "Amazon.pl": "#1baf7a"}
TEXT, TEXT2, MUTED, GRID = "#0b0b0b", "#52514e", "#77766f", "#e9e8e3"
LEVEL_COLOR = {"critical": "#d03b3b", "warning": "#fab219", "good": "#0ca30c"}
LEVEL_NAME = {"critical": "Wymaga działania", "warning": "Do obserwacji", "good": "Pozytywne"}
MONTHS = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]


def setup_fonts() -> None:
    names = {f.name for f in font_manager.fontManager.ttflist}
    family = "Inter" if "Inter" in names else "DejaVu Sans"
    plt.rcParams.update({"font.family": family, "svg.fonttype": "none", "font.size": 9,
                         "axes.edgecolor": GRID, "axes.labelcolor": TEXT2, "xtick.color": MUTED, "ytick.color": MUTED})


def d_pl(ts) -> str:
    return f"{ts.day} {MONTHS[ts.month - 1]} {ts.year}"


def svg_trend(s: WeekSummary) -> str:
    tr = s.trend
    fig, ax = plt.subplots(figsize=(7.2, 2.7), dpi=100)
    x = range(len(tr))
    for ch in CHANNEL_ORDER:
        ax.plot(x, tr[ch].values, color=COLORS[ch], lw=2, solid_capstyle="round")
        ax.scatter([len(tr) - 1], [tr[ch].values[-1]], s=22, color=COLORS[ch], zorder=3, edgecolor="white", linewidth=1.5)
        ax.annotate(ch, (len(tr) - 1, tr[ch].values[-1]), xytext=(8, 0), textcoords="offset points",
                    va="center", fontsize=8.5, color=TEXT2, fontweight="semibold")
    ax.axvspan(len(tr) - 1.5, len(tr) - 0.5, color="#f0efec", zorder=0)
    ax.set_xticks(list(x))
    ax.set_xticklabels([w.split("-")[1] for w in tr.index], fontsize=8)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v / 1000:.0f} tys." if v else "0"))
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", color=GRID, lw=1)
    ax.set_axisbelow(True)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(length=0)
    ax.set_xlim(-0.3, len(tr) - 0.3 + 1.6)
    fig.tight_layout(pad=0.4)
    buf = io.StringIO()
    fig.savefig(buf, format="svg", transparent=True)
    plt.close(fig)
    svg = buf.getvalue()
    return svg[svg.index("<svg"):]


def delta_html(cur, prev, inverse=False, pp=False) -> str:
    if cur is None or prev is None:
        return '<span class="muted">–</span>'
    ch = (cur - prev) if pp else pct_change(cur, prev)
    if ch is None:
        return '<span class="muted">–</span>'
    good = (ch >= 0) != inverse
    cls = "good" if good else "bad"
    arrow = "▲" if ch >= 0 else "▼"
    num = f"{ch:+.1f}".replace(".", ",")
    txt = f"{num} p.p." if pp else f"{num}%"
    return f'<span class="{cls}">{arrow} {txt}</span>'


def recommendations(s: WeekSummary) -> list[str]:
    rec = []
    for a in s.alerts:
        t = a["title"]
        if t.startswith("Możliwy brak towaru"):
            rec.append(f"Zweryfikuj stan magazynowy i status oferty: {html.escape(t.split(': ', 1)[1])}. "
                       "Jeśli towar jest niedostępny – ustaw alert niskiego stanu w systemie magazynowym.")
        elif t.startswith("Spadek przychodu"):
            rec.append(f"Przeanalizuj przyczynę spadku ({html.escape(t.split(': ', 1)[1])}): dostępność ofert, ceny konkurencji, "
                       "pozycję w wynikach wyszukiwania kanału.")
        elif t.startswith("Niski ROAS"):
            rec.append("Przejrzyj kampanie z najniższym ROAS, przesuń budżet do kampanii z ROAS powyżej progu.")
        elif t.startswith("Wysoki odsetek zwrotów"):
            rec.append("Sprawdź powody zwrotów w ostatnim tygodniu (rozmiar akcesoriów, uszkodzenia w transporcie, opisy produktów).")
        elif t.startswith("Najszybciej rosnący"):
            rec.append(f"Wykorzystaj wzrost: {html.escape(t.split(': ', 1)[1])} – rozważ poszerzenie oferty i budżetu w tym kanale.")
    return rec or ["Brak odchyleń od progów – utrzymaj bieżące działania."]


CSS = """
@page { size: A4; margin: 14mm 14mm 12mm; }
* { box-sizing: border-box; }
body { font-family: Inter, 'Segoe UI', system-ui, sans-serif; color: #0b0b0b; font-size: 10.5pt; line-height: 1.45; margin: 0;
  font-feature-settings: "tnum" 1; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.page { max-width: 182mm; margin: 0 auto; }
.head { display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid #0b0b0b; padding-bottom: 8px; margin-bottom: 14px; }
.head h1 { font-size: 18pt; margin: 0; letter-spacing: -.01em; }
.head .meta { text-align: right; color: #52514e; font-size: 9pt; }
.logo { display: inline-grid; place-items: center; width: 26px; height: 26px; border-radius: 7px; background: #0b0b0b; color: #fff; font-size: 9pt; font-weight: 700; margin-right: 8px; vertical-align: 3px; }
h2 { font-size: 11.5pt; margin: 16px 0 6px; }
.lead { font-size: 11pt; margin: 0 0 12px; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.kpi { border: 1px solid #e2e1dc; border-radius: 8px; padding: 8px 10px; background: #fcfcfb; }
.kpi .l { font-size: 8.5pt; color: #52514e; }
.kpi .v { font-size: 15pt; font-weight: 650; letter-spacing: -.02em; }
.kpi .d { font-size: 8.5pt; color: #77766f; }
.good { color: #006300; font-weight: 600; } .bad { color: #b42727; font-weight: 600; } .muted { color: #77766f; }
.alert { display: flex; gap: 10px; border: 1px solid #e2e1dc; border-left-width: 4px; border-radius: 6px; padding: 7px 10px; margin-bottom: 6px; }
.alert .lvl { font-size: 8pt; color: #77766f; text-transform: uppercase; letter-spacing: .04em; }
.alert b { display: block; }
.alert .det { color: #52514e; font-size: 9.5pt; }
table { width: 100%; border-collapse: collapse; font-size: 9.5pt; }
th { text-align: left; font-weight: 500; color: #77766f; font-size: 8.5pt; border-bottom: 1px solid #e2e1dc; padding: 4px 6px; }
td { padding: 5px 6px; border-bottom: 1px solid #efeee9; }
td.n, th.n { text-align: right; white-space: nowrap; }
tr.total td { font-weight: 650; border-top: 1px solid #0b0b0b; border-bottom: 0; }
.sw { display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 6px; }
.chart svg { width: 100%; height: auto; }
ol.rec { margin: 4px 0 0; padding-left: 18px; } ol.rec li { margin-bottom: 4px; }
.cols { display: grid; grid-template-columns: 1.35fr 1fr; gap: 14px; }
.foot { margin-top: 16px; padding-top: 6px; border-top: 1px solid #e2e1dc; color: #77766f; font-size: 8pt; display: flex; justify-content: space-between; }
.break { break-before: page; }
"""


def build_html(s: WeekSummary, trend_svg: str) -> str:
    t, p = s.total, s.total_prev
    rev_chg = pct_change(t["revenue"], p["revenue"])
    lead = (f"Przychód netto w tygodniu {s.week.split('-W')[1]} wyniósł <b>{fmt_pln(t['revenue'])}</b> "
            f"({fmt_pct(rev_chg)} t/t) przy <b>{t['orders']}</b> zamówieniach i marży brutto <b>{fmt_pct(t['gross_margin_pct'], False)}</b>. "
            f"Alerty wymagające działania: <b>{sum(a['level'] == 'critical' for a in s.alerts)}</b>.")

    kpi_defs = [("Przychód netto", fmt_pln(t["revenue"]), delta_html(t["revenue"], p["revenue"])),
                ("Zamówienia", f"{t['orders']}", delta_html(t["orders"], p["orders"])),
                ("Średnia wartość zamówienia", fmt_pln(t["aov"]), delta_html(t["aov"], p["aov"])),
                ("Marża brutto", fmt_pct(t["gross_margin_pct"], False), delta_html(t["gross_margin_pct"], p["gross_margin_pct"], pp=True)),
                ("Wydatki reklamowe", fmt_pln(t["ad_spend"]), delta_html(t["ad_spend"], p["ad_spend"], inverse=True)),
                ("ROAS", f"{t['roas']:.1f}×".replace(".", ","), delta_html(t["roas"], p["roas"])),
                ("Marża po reklamie", fmt_pln(t["contribution"]), delta_html(t["contribution"], p["contribution"])),
                ("Odsetek zwrotów", fmt_pct(t["return_rate_pct"], False), delta_html(t["return_rate_pct"], p["return_rate_pct"], inverse=True, pp=True))]
    kpis = "".join(f'<div class="kpi"><div class="l">{l}</div><div class="v">{v}</div><div class="d">{d} t/t</div></div>' for l, v, d in kpi_defs)

    alerts = "".join(
        f'<div class="alert" style="border-left-color:{LEVEL_COLOR[a["level"]]}"><div><span class="lvl">{LEVEL_NAME[a["level"]]}</span>'
        f'<b>{html.escape(a["title"])}</b><span class="det">{html.escape(a["detail"])}</span></div></div>' for a in s.alerts
    ) or '<p class="muted">Brak alertów – wszystkie wskaźniki w normie.</p>'

    ch_rows = ""
    for ch in CHANNEL_ORDER:
        c, cp = s.by_channel[ch], s.by_channel_prev[ch]
        roas = f"{c['roas']:.1f}×".replace(".", ",") if c["roas"] else "–"
        ch_rows += (f'<tr><td><span class="sw" style="background:{COLORS[ch]}"></span>{ch}</td><td class="n">{fmt_pln(c["revenue"])}</td>'
                    f'<td class="n">{delta_html(c["revenue"], cp["revenue"])}</td><td class="n">{c["orders"]}</td>'
                    f'<td class="n">{fmt_pln(c["aov"])}</td><td class="n">{fmt_pct(c["gross_margin_pct"], False)}</td>'
                    f'<td class="n">{fmt_pln(c["ad_spend"])}</td><td class="n">{roas}</td><td class="n">{fmt_pln(c["contribution"])}</td></tr>')
    roas_t = f"{t['roas']:.1f}×".replace(".", ",")
    ch_rows += (f'<tr class="total"><td>Razem</td><td class="n">{fmt_pln(t["revenue"])}</td><td class="n">{delta_html(t["revenue"], p["revenue"])}</td>'
                f'<td class="n">{t["orders"]}</td><td class="n">{fmt_pln(t["aov"])}</td><td class="n">{fmt_pct(t["gross_margin_pct"], False)}</td>'
                f'<td class="n">{fmt_pln(t["ad_spend"])}</td><td class="n">{roas_t}</td><td class="n">{fmt_pln(t["contribution"])}</td></tr>')

    top_rows = "".join(
        f'<tr><td>{i}. {html.escape(r.product_name)}</td><td class="n">{int(r.units)}</td><td class="n">{fmt_pln(r.revenue)}</td>'
        f'<td class="n">{delta_html(r.revenue, r.revenue_prev if r.revenue_prev == r.revenue_prev else None)}</td></tr>'
        for i, r in enumerate(s.top_products.itertuples(), 1))
    cat_rows = "".join(f'<tr><td>{html.escape(r.category)}</td><td class="n">{fmt_pln(r.revenue)}</td><td class="n">{fmt_pct(r.margin_pct, False)}</td></tr>'
                       for r in s.category.itertuples())
    rec = "".join(f"<li>{r}</li>" for r in recommendations(s))

    return f"""<!DOCTYPE html><html lang="pl"><head><meta charset="utf-8"><title>{STORE_NAME} – raport tygodniowy {s.week}</title><style>{CSS}</style></head>
<body><div class="page">
<div class="head"><div><h1><span class="logo">VF</span>Raport tygodniowy sprzedaży</h1></div>
<div class="meta"><b>{STORE_NAME}</b> · tydzień {s.week}<br>{d_pl(s.start)} – {d_pl(s.end)} · porównanie z {s.prev_week}</div></div>
<p class="lead">{lead}</p>
<div class="kpis">{kpis}</div>
<h2>Alerty i sygnały</h2>{alerts}
<h2>Wyniki według kanału</h2>
<table><thead><tr><th>Kanał</th><th class="n">Przychód</th><th class="n">t/t</th><th class="n">Zam.</th><th class="n">AOV</th><th class="n">Marża</th><th class="n">Reklama</th><th class="n">ROAS</th><th class="n">Po reklamie</th></tr></thead><tbody>{ch_rows}</tbody></table>
<div class="break"></div>
<h2>Przychód netto – ostatnie 12 tygodni</h2>
<div class="chart">{trend_svg}</div>
<div class="cols">
<div><h2>Top produkty tygodnia</h2><table><thead><tr><th>Produkt</th><th class="n">Szt.</th><th class="n">Przychód</th><th class="n">t/t</th></tr></thead><tbody>{top_rows}</tbody></table></div>
<div><h2>Kategorie</h2><table><thead><tr><th>Kategoria</th><th class="n">Przychód</th><th class="n">Marża</th></tr></thead><tbody>{cat_rows}</tbody></table>
<h2>Rekomendowane działania</h2><ol class="rec">{rec}</ol></div>
</div>
<div class="foot"><span>Kwoty netto w PLN. Marża brutto = przychód − koszt zakupu − prowizje kanałów. Progi alertów: spadek kanału ≤ {ALERTS['channel_revenue_drop_pct']:.0f}%, ROAS &lt; {ALERTS['roas_min']:.0f}, zwroty &gt; {ALERTS['return_rate_max_pct']:.0f}%.</span><span>Wygenerowano automatycznie · dane demonstracyjne</span></div>
</div></body></html>"""


def build_email(s: WeekSummary, dashboard_url: str) -> str:
    t, p = s.total, s.total_prev

    def cell(label, val, d):
        return (f'<td style="padding:10px 12px;border:1px solid #e2e1dc;border-radius:8px;background:#fcfcfb;width:25%">'
                f'<div style="font-size:12px;color:#52514e">{label}</div><div style="font-size:20px;font-weight:700;color:#0b0b0b">{val}</div>'
                f'<div style="font-size:12px">{d}</div></td>')
    d = lambda c, pv, **kw: delta_html(c, pv, **kw).replace('class="good"', 'style="color:#006300;font-weight:600"').replace('class="bad"', 'style="color:#b42727;font-weight:600"').replace('class="muted"', 'style="color:#77766f"')
    kpis = (cell("Przychód netto", fmt_pln(t["revenue"]), d(t["revenue"], p["revenue"])) +
            cell("Zamówienia", str(t["orders"]), d(t["orders"], p["orders"])) +
            cell("Marża brutto", fmt_pct(t["gross_margin_pct"], False), d(t["gross_margin_pct"], p["gross_margin_pct"], pp=True)) +
            cell("ROAS", f"{t['roas']:.1f}×".replace(".", ","), d(t["roas"], p["roas"])))
    alerts = "".join(
        f'<tr><td style="padding:8px 10px;border-left:4px solid {LEVEL_COLOR[a["level"]]};background:#f6f5f2">'
        f'<div style="font-size:11px;color:#77766f;text-transform:uppercase">{LEVEL_NAME[a["level"]]}</div>'
        f'<div style="font-weight:600">{html.escape(a["title"])}</div><div style="color:#52514e;font-size:13px">{html.escape(a["detail"])}</div></td></tr>'
        f'<tr><td style="height:6px"></td></tr>' for a in s.alerts)
    return f"""<!DOCTYPE html><html lang="pl"><head><meta charset="utf-8"></head>
<body style="margin:0;background:#f4f3ef;font-family:'Segoe UI',Arial,sans-serif;color:#0b0b0b">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px">
<table role="presentation" width="640" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;padding:24px">
<tr><td><div style="font-size:13px;color:#77766f">{STORE_NAME} · tydzień {s.week} ({d_pl(s.start)} – {d_pl(s.end)})</div>
<h1 style="font-size:22px;margin:4px 0 16px">Raport tygodniowy sprzedaży</h1></td></tr>
<tr><td><table role="presentation" width="100%" cellspacing="6"><tr>{kpis}</tr></table></td></tr>
<tr><td><h2 style="font-size:16px;margin:18px 0 8px">Alerty</h2><table role="presentation" width="100%" cellspacing="0">{alerts}</table></td></tr>
<tr><td style="padding-top:14px"><a href="{dashboard_url}" style="display:inline-block;background:#0b0b0b;color:#fff;text-decoration:none;padding:10px 16px;border-radius:8px;font-weight:600">Otwórz dashboard</a>
<span style="color:#77766f;font-size:13px;margin-left:10px">Pełny raport w załączniku (PDF).</span></td></tr>
</table><div style="font-size:11px;color:#77766f;margin-top:10px">Wiadomość wygenerowana automatycznie.</div></td></tr></table></body></html>"""


def to_pdf(html_path: Path, pdf_path: Path) -> bool:
    chrome = next((shutil.which(b) for b in ("google-chrome", "chromium", "chromium-browser", "chrome") if shutil.which(b)), None)
    if not chrome:
        print("  ! Nie znaleziono Chrome/Chromium – pomijam PDF (HTML gotowy do wydruku).")
        return False
    subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True


def main(week: str | None = None, dashboard_url: str = "https://example.com/dashboard") -> dict:
    setup_fonts()
    orders, mk = load()
    s = week_summary(orders, mk, week)
    out = REPORTS_DIR / s.week
    out.mkdir(parents=True, exist_ok=True)

    html_path = out / f"raport_{s.week}.html"
    html_path.write_text(build_html(s, svg_trend(s)), encoding="utf-8")
    pdf_path = out / f"raport_{s.week}.pdf"
    has_pdf = to_pdf(html_path, pdf_path)
    (out / f"email_{s.week}.html").write_text(build_email(s, dashboard_url), encoding="utf-8")

    t = s.total
    summary = {
        "week": s.week, "date_from": s.start.date().isoformat(), "date_to": s.end.date().isoformat(),
        "kpi": {k: (round(v, 2) if isinstance(v, float) else v) for k, v in t.items()},
        "kpi_change_pct": {k: (round(pct_change(t[k], s.total_prev[k]), 1) if pct_change(t[k], s.total_prev[k]) is not None else None)
                           for k in ("revenue", "orders", "aov", "roas", "contribution")},
        "alerts": s.alerts,
        "critical_alerts": sum(a["level"] == "critical" for a in s.alerts),
        "slack_text": (f"*Raport tygodniowy {STORE_NAME} – {s.week}*\n"
                       f"Przychód: {fmt_pln(t['revenue'])} ({fmt_pct(pct_change(t['revenue'], s.total_prev['revenue']))} t/t) · "
                       f"Zamówienia: {t['orders']} · ROAS: {t['roas']:.1f}\n" +
                       "\n".join(f"{':red_circle:' if a['level'] == 'critical' else ':large_yellow_circle:' if a['level'] == 'warning' else ':large_green_circle:'} {a['title']}" for a in s.alerts)),
        "files": {"pdf": pdf_path.name if has_pdf else None, "email_html": f"email_{s.week}.html"},
    }
    (out / f"summary_{s.week}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Raport {s.week}: {out.relative_to(REPORTS_DIR.parent)} | alerty: {len(s.alerts)}")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generuje raport tygodniowy sprzedaży")
    ap.add_argument("--week", help="Tydzień ISO, np. 2026-W47 (domyślnie ostatni pełny)")
    ap.add_argument("--dashboard-url", default="https://example.com/dashboard")
    a = ap.parse_args()
    main(a.week, a.dashboard_url)
