"""
Etap 2 pipeline'u: definicje KPI i reguły alertów – jedno źródło prawdy dla raportu i dashboardu.

Wszystkie kwoty netto w PLN. Zwrócone zamówienia pomniejszają przychód netto i marżę.
"""
from dataclasses import dataclass, field

import pandas as pd

from config import ALERTS, CHANNEL_ORDER, DATA_PROCESSED


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    orders = pd.read_csv(DATA_PROCESSED / "orders_clean.csv", parse_dates=["order_ts", "date"])
    mk = pd.read_csv(DATA_PROCESSED / "marketing_clean.csv", parse_dates=["date"])
    return orders, mk


def kpi_block(o: pd.DataFrame, mk: pd.DataFrame) -> dict:
    """KPI dla dowolnego wycinka danych (okres / kanał)."""
    kept = o[o.is_returned == 0]
    orders_n = o.order_id.nunique()
    revenue = kept.revenue.sum()
    margin = kept.gross_margin.sum()
    spend = mk.spend_pln.sum()
    customers = o.customer_id.nunique()
    new_c = o[o.is_new_customer == 1].customer_id.nunique()
    return {
        "revenue": revenue,
        "orders": orders_n,
        "aov": revenue / max(kept.order_id.nunique(), 1),
        "gross_margin": margin,
        "gross_margin_pct": 100 * margin / revenue if revenue else 0.0,
        "ad_spend": spend,
        "roas": revenue / spend if spend else None,
        "contribution": margin - spend,
        "return_rate_pct": 100 * o[o.is_returned == 1].order_id.nunique() / max(orders_n, 1),
        "units": int(kept.quantity.sum()),
        "customers": customers,
        "new_customers": new_c,
        "returning_share_pct": 100 * (customers - new_c) / max(customers, 1),
        "cac": spend / new_c if new_c else None,
    }


def pct_change(cur: float | None, prev: float | None) -> float | None:
    if cur is None or prev in (None, 0):
        return None
    return 100 * (cur - prev) / abs(prev)


@dataclass
class WeekSummary:
    week: str
    prev_week: str
    start: pd.Timestamp
    end: pd.Timestamp
    total: dict
    total_prev: dict
    by_channel: dict = field(default_factory=dict)
    by_channel_prev: dict = field(default_factory=dict)
    alerts: list = field(default_factory=list)
    top_products: pd.DataFrame | None = None
    category: pd.DataFrame | None = None
    daily: pd.DataFrame | None = None
    trend: pd.DataFrame | None = None


def weeks_available(orders: pd.DataFrame) -> list[str]:
    return sorted(orders.iso_week.unique())


def week_summary(orders: pd.DataFrame, mk: pd.DataFrame, week: str | None = None) -> WeekSummary:
    weeks = weeks_available(orders)
    week = week or weeks[-1]
    i = weeks.index(week)
    prev = weeks[i - 1]

    o_w, o_p = orders[orders.iso_week == week], orders[orders.iso_week == prev]
    m_w, m_p = mk[mk.iso_week == week], mk[mk.iso_week == prev]
    s = WeekSummary(week=week, prev_week=prev, start=o_w.date.min(), end=o_w.date.max(),
                    total=kpi_block(o_w, m_w), total_prev=kpi_block(o_p, m_p))
    for ch in CHANNEL_ORDER:
        s.by_channel[ch] = kpi_block(o_w[o_w.channel == ch], m_w[m_w.channel == ch])
        s.by_channel_prev[ch] = kpi_block(o_p[o_p.channel == ch], m_p[m_p.channel == ch])

    kept_w = o_w[o_w.is_returned == 0]
    kept_p = o_p[o_p.is_returned == 0]
    tp = kept_w.groupby(["sku", "product_name"]).agg(units=("quantity", "sum"), revenue=("revenue", "sum")).reset_index()
    tp_prev = kept_p.groupby("sku").revenue.sum().rename("revenue_prev")
    s.top_products = tp.merge(tp_prev, on="sku", how="left").sort_values("revenue", ascending=False).head(8)

    cat = kept_w.groupby("category").agg(revenue=("revenue", "sum"), margin=("gross_margin", "sum")).reset_index()
    cat["margin_pct"] = 100 * cat.margin / cat.revenue
    s.category = cat.sort_values("revenue", ascending=False)

    s.daily = kept_w.groupby([kept_w.date.dt.date, "channel"]).revenue.sum().unstack(fill_value=0).reindex(columns=CHANNEL_ORDER, fill_value=0)

    # trend 12 tygodni
    last12 = weeks[max(0, i - 11): i + 1]
    tr = orders[orders.iso_week.isin(last12) & (orders.is_returned == 0)]
    s.trend = tr.groupby(["iso_week", "channel"]).revenue.sum().unstack(fill_value=0).reindex(columns=CHANNEL_ORDER, fill_value=0)

    s.alerts = build_alerts(orders, s, weeks[max(0, i - 4): i])
    return s


def build_alerts(orders: pd.DataFrame, s: WeekSummary, baseline_weeks: list[str]) -> list[dict]:
    """Reguły biznesowe -> lista alertów {level, title, detail}. level: critical / warning / good."""
    a = []
    for ch in CHANNEL_ORDER:
        cur, prev = s.by_channel[ch], s.by_channel_prev[ch]
        chg = pct_change(cur["revenue"], prev["revenue"])
        drop_pln = prev["revenue"] - cur["revenue"]
        if chg is not None and chg <= ALERTS["channel_revenue_drop_pct"] and drop_pln >= ALERTS["channel_revenue_drop_min_pln"]:
            a.append({"level": "critical", "title": f"Spadek przychodu: {ch} {chg:+.0f}% t/t",
                      "detail": f"{fmt_pln(cur['revenue'])} vs {fmt_pln(prev['revenue'])} tydzień wcześniej."})
        if cur["roas"] is not None and cur["roas"] < ALERTS["roas_min"]:
            a.append({"level": "warning", "title": f"Niski ROAS: {ch} {cur['roas']:.1f}",
                      "detail": f"Wydatki {fmt_pln(cur['ad_spend'])} przy przychodzie {fmt_pln(cur['revenue'])}. "
                                f"Próg: {ALERTS['roas_min']:.1f}."})

    if s.total["return_rate_pct"] > ALERTS["return_rate_max_pct"]:
        a.append({"level": "warning", "title": f"Wysoki odsetek zwrotów: {s.total['return_rate_pct']:.1f}%",
                  "detail": f"Próg: {ALERTS['return_rate_max_pct']:.0f}% zamówień."})

    # wykrywanie braków towaru: produkt sprzedawał się regularnie w kanale, a w tym tygodniu 0 szt.
    base = orders[orders.iso_week.isin(baseline_weeks) & (orders.is_returned == 0)]
    per_week = base.groupby(["channel", "sku", "product_name", "iso_week"]).quantity.sum()
    stats = per_week.groupby(level=[0, 1, 2]).agg(["sum", "count"])
    cur = orders[(orders.iso_week == s.week)].groupby(["channel", "sku"]).quantity.sum()
    for (ch, sku, name), row in stats.iterrows():
        avg = row["sum"] / max(len(baseline_weeks), 1)
        sold_every_week = row["count"] == len(baseline_weeks)
        if sold_every_week and avg >= ALERTS["stockout_min_weekly_units"] and cur.get((ch, sku), 0) == 0:
            a.append({"level": "critical", "title": f"Możliwy brak towaru: {name} ({ch})",
                      "detail": f"Średnio {avg:.0f} szt./tydz. w ostatnich {len(baseline_weeks)} tygodniach, "
                                f"w tym tygodniu 0 szt. Sprawdź stan magazynowy i aktywność oferty."})

    best = max(CHANNEL_ORDER, key=lambda c: pct_change(s.by_channel[c]["revenue"], s.by_channel_prev[c]["revenue"]) or -999)
    chg = pct_change(s.by_channel[best]["revenue"], s.by_channel_prev[best]["revenue"])
    if chg is not None and chg > 5:
        a.append({"level": "good", "title": f"Najszybciej rosnący kanał: {best} {chg:+.0f}% t/t",
                  "detail": f"Przychód {fmt_pln(s.by_channel[best]['revenue'])}."})

    order = {"critical": 0, "warning": 1, "good": 2}
    return sorted(a, key=lambda x: order[x["level"]])


def fmt_pln(v: float | None, decimals: int = 0) -> str:
    if v is None:
        return "–"
    s = f"{v:,.{decimals}f}".replace(",", " ").replace(".", ",")
    return f"{s} zł"


def fmt_pct(v: float | None, signed: bool = True) -> str:
    if v is None:
        return "–"
    return (f"{v:+.1f}%" if signed else f"{v:.1f}%").replace(".", ",")


if __name__ == "__main__":
    o, m = load()
    s = week_summary(o, m)
    print(s.week, s.start.date(), s.end.date())
    for k, v in s.total.items():
        print(f"  {k}: {v}  (poprz. {s.total_prev[k]})")
    for al in s.alerts:
        print(al)
