"""
Etap 3 pipeline'u: buduje samodzielny plik dashboard/index.html.

Dane trafiają do HTML jako kompaktowy JSON (tablice zamiast obiektów), a cała agregacja
i filtrowanie dzieje się w przeglądarce – plik działa offline, bez serwera i bez bibliotek.
"""
import json
from datetime import date, datetime

import pandas as pd

from config import CHANNEL_ORDER, DASHBOARD_DIR, ROOT, STORE_NAME
from kpis import load

TEMPLATE = ROOT / "src" / "templates" / "dashboard_template.html"


def main() -> None:
    orders, mk = load()
    start = orders.date.min().date()
    products = orders[["sku", "product_name", "category"]].drop_duplicates("sku").sort_values("sku").reset_index(drop=True)
    categories = sorted(products.category.unique())
    p_idx = {s: i for i, s in enumerate(products.sku)}
    c_idx = {c: i for i, c in enumerate(CHANNEL_ORDER)}
    o_idx = {o: i for i, o in enumerate(orders.order_id.unique())}

    day = (orders.date.dt.date - start).map(lambda d: d.days)
    rows = list(zip(
        day.tolist(), orders.hour.tolist(), orders.channel.map(c_idx).tolist(), orders.sku.map(p_idx).tolist(),
        orders.quantity.tolist(), orders.revenue.round(2).tolist(), orders.gross_margin.round(2).tolist(),
        orders.is_returned.tolist(), orders.is_new_customer.tolist(), orders.order_id.map(o_idx).tolist(),
        orders.customer_id.tolist(),
    ))
    mk_day = (mk.date.dt.date - start).map(lambda d: d.days)
    mk_rows = list(zip(mk_day.tolist(), mk.channel.map(c_idx).tolist(), mk.spend_pln.round(2).tolist()))

    payload = {
        "store": STORE_NAME,
        "start": start.isoformat(),
        "end": orders.date.max().date().isoformat(),
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "channels": CHANNEL_ORDER,
        "categories": categories,
        "products": [[r.sku, r.product_name, categories.index(r.category)] for r in products.itertuples()],
        "cols": ["day", "hour", "ch", "prod", "qty", "rev", "margin", "ret", "new", "order", "cust"],
        "rows": rows,
        "mk": mk_rows,
    }
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", data)
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    out = DASHBOARD_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"dashboard/index.html: {out.stat().st_size / 1024:.0f} KB, {len(rows):,} pozycji")


if __name__ == "__main__":
    main()
