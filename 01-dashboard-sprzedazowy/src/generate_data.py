"""
Generator realistycznych danych demonstracyjnych dla fikcyjnego sklepu z suplementami VitaForge.

Symuluje eksport z trzech kanałów (Sklep WWW / Allegro / Amazon.pl) za 52 tygodnie:
sezonowość (styczniowe postanowienia, wakacyjny dołek, Black Friday), wzrost trendu,
rosnący udział Amazona, klientów powracających, zwroty, kody rabatowe oraz wydatki reklamowe.

Celowo dodaje typowe problemy z jakością danych, które pipeline musi wyczyścić:
duplikaty wierszy, zamówienia testowe, mieszane formaty dat, przecinek dziesiętny,
niespójne nazwy kanałów, brakujący kanał, białe znaki w nazwach produktów.

W ostatnim pełnym tygodniu jest "ukryta historia" do wykrycia przez alerty:
brak towaru (kreatyna 500 g) na Allegro.
"""
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from config import DATA_RAW

SEED = 42
START = date(2025, 11, 24)   # poniedziałek
END = date(2026, 11, 22)     # niedziela – koniec ostatniego pełnego tygodnia
STOCKOUT_SKU = "KRE-500"
STOCKOUT_FROM = date(2026, 11, 16)

PRODUCTS = [
    # sku, nazwa, kategoria, cena netto, koszt zakupu (COGS), popularność
    ("WHY-900", "Białko Whey 900 g", "Białko", 119.0, 62.0, 10),
    ("WHY-2K", "Białko Whey 2 kg", "Białko", 219.0, 118.0, 4),
    ("ISO-700", "Izolat białka 700 g", "Białko", 149.0, 82.0, 5),
    ("VEG-750", "Białko roślinne 750 g", "Białko", 109.0, 58.0, 3),
    ("KAZ-700", "Kazeina 700 g", "Białko", 129.0, 70.0, 2),
    ("KRE-500", "Kreatyna monohydrat 500 g", "Kreatyna", 79.0, 28.0, 9),
    ("KRE-250", "Kreatyna monohydrat 250 g", "Kreatyna", 49.0, 18.0, 5),
    ("KRE-CAP", "Kreatyna kapsułki 240 szt.", "Kreatyna", 69.0, 26.0, 3),
    ("KRE-ALK", "Kre-Alkalyn 120 kaps.", "Kreatyna", 89.0, 38.0, 1.5),
    ("VIT-D3K2", "Witamina D3 + K2", "Witaminy i zdrowie", 39.0, 11.0, 7),
    ("OMG-120", "Omega-3 120 kaps.", "Witaminy i zdrowie", 59.0, 22.0, 6),
    ("MAG-B6", "Magnez + B6", "Witaminy i zdrowie", 29.0, 8.0, 6),
    ("MULTI", "Multiwitamina Active", "Witaminy i zdrowie", 49.0, 16.0, 4),
    ("ASHW", "Ashwagandha KSM-66", "Witaminy i zdrowie", 55.0, 17.0, 4),
    ("ZINC", "Cynk 25 mg", "Witaminy i zdrowie", 25.0, 6.0, 3),
    ("PRE-300", "Przedtreningówka 300 g", "Przedtreningówki", 99.0, 38.0, 5),
    ("BETA-200", "Beta-alanina 200 g", "Przedtreningówki", 59.0, 21.0, 2),
    ("CIT-300", "Cytrulina 300 g", "Przedtreningówki", 79.0, 31.0, 2),
    ("CAF-200", "Kofeina 200 kaps.", "Przedtreningówki", 29.0, 8.0, 3),
    ("SHK-700", "Shaker 700 ml", "Akcesoria", 25.0, 7.0, 5),
    ("BELT", "Pas treningowy", "Akcesoria", 89.0, 39.0, 1.5),
    ("GLOV", "Rękawiczki treningowe", "Akcesoria", 59.0, 22.0, 1.5),
    ("BAND", "Taśmy oporowe (zestaw)", "Akcesoria", 69.0, 24.0, 2),
    ("BOT-1L", "Bidon 1 l", "Akcesoria", 35.0, 11.0, 2),
]

MONTH_SEASON = {1: 1.38, 2: 1.15, 3: 1.06, 4: 1.0, 5: 1.04, 6: 0.9,
                7: 0.8, 8: 0.85, 9: 1.1, 10: 1.05, 11: 1.0, 12: 0.92}
WEEKDAY = [1.15, 1.08, 1.0, 0.96, 0.88, 0.84, 1.08]  # pon..nd
HOUR_W = np.array([1, 0.5, 0.3, 0.2, 0.2, 0.4, 1.2, 2.4, 3.0, 3.2, 3.4, 3.6,
                   4.0, 3.8, 3.6, 3.8, 4.2, 4.8, 5.6, 6.6, 7.2, 6.8, 4.8, 2.6])
HOUR_W = HOUR_W / HOUR_W.sum()

# Black Friday 2025 = 28.11, Cyber Monday = 1.12
SPECIAL_DAYS = {date(2025, 11, 27): 1.6, date(2025, 11, 28): 3.1, date(2025, 11, 29): 2.2,
                date(2025, 11, 30): 1.8, date(2025, 12, 1): 2.4, date(2025, 12, 2): 1.3,
                date(2025, 12, 15): 1.25, date(2025, 12, 16): 1.2, date(2025, 12, 24): 0.4,
                date(2025, 12, 25): 0.3, date(2025, 12, 26): 0.6, date(2026, 1, 1): 0.7,
                date(2026, 1, 2): 1.5, date(2026, 1, 5): 1.6, date(2026, 4, 5): 0.5,
                date(2026, 4, 6): 0.6, date(2026, 11, 11): 1.5}

BASE_DAILY_ORDERS = 32.0


def season(d: date) -> float:
    """Sezonowość miesięczna interpolowana liniowo między środkami miesięcy (bez skoków na przełomie)."""
    pos = d.month - 1 + (d.day - 15) / 30.0
    lo = int(np.floor(pos)) % 12
    hi = (lo + 1) % 12
    t = pos - np.floor(pos)
    return MONTH_SEASON[lo + 1] * (1 - t) + MONTH_SEASON[hi + 1] * t


def is_promo_period(d: date) -> bool:
    return date(2025, 11, 27) <= d <= date(2025, 12, 2)


def main() -> None:
    rng = np.random.default_rng(SEED)
    DATA_RAW.mkdir(parents=True, exist_ok=True)

    prod = pd.DataFrame(PRODUCTS, columns=["sku", "product_name", "category", "unit_price", "unit_cost", "popularity"])
    total_days = (END - START).days + 1
    sku_idx = {s: i for i, s in enumerate(prod.sku)}

    rows, ad_rows = [], []
    customers: list[int] = []
    cust_orders = np.zeros(20000)
    order_no = {"WWW": 100000, "ALG": 500000, "AMZ": 800000}

    for di in range(total_days):
        d = START + timedelta(days=di)
        progress = di / total_days
        trend = 1.0 + 0.28 * progress
        lam = BASE_DAILY_ORDERS * trend * season(d) * WEEKDAY[d.weekday()] * SPECIAL_DAYS.get(d, 1.0)
        n_orders = rng.poisson(lam)

        # udział kanałów: Amazon rośnie z ~6% do ~17%
        amz = 0.06 + 0.11 * progress
        alg = 0.37 - 0.03 * progress
        p_ch = np.array([1 - amz - alg, alg, amz])

        # w styczniu więcej białka i kreatyny, w grudniu więcej akcesoriów (prezenty)
        pop = prod.popularity.to_numpy(dtype=float).copy()
        if d.month == 1:
            pop[prod.category.isin(["Białko", "Kreatyna"]).to_numpy()] *= 1.3
        if d.month == 12:
            pop[(prod.category == "Akcesoria").to_numpy()] *= 2.0
        if d.month in (10, 11, 12, 1, 2):
            pop[prod.sku.isin(["VIT-D3K2", "OMG-120", "ZINC"]).to_numpy()] *= 1.6

        for _ in range(n_orders):
            ch = rng.choice(["WWW", "ALG", "AMZ"], p=p_ch)
            order_no[ch] += int(rng.integers(1, 4))
            oid = f"{ch}-{order_no[ch]}"

            p_return = 0.22 + 0.2 * progress
            if customers and rng.random() < p_return:
                w = 1 + cust_orders[:len(customers)]
                cid = customers[int(rng.choice(len(customers), p=w / w.sum()))]
            else:
                cid = 10001 + len(customers)
                customers.append(cid)
            cust_orders[cid - 10001] += 1

            hour = int(rng.choice(24, p=HOUR_W))
            ts = datetime(d.year, d.month, d.day, hour, int(rng.integers(0, 60)), int(rng.integers(0, 60)))

            n_lines = 1 + min(rng.poisson(0.75), 4)
            pp = pop / pop.sum()
            skus = rng.choice(len(prod), size=n_lines, replace=False, p=pp)

            discount = 0.0
            if ch == "WWW":
                if is_promo_period(d):
                    discount = 0.25
                elif rng.random() < 0.18:
                    discount = float(rng.choice([0.10, 0.15]))
            elif is_promo_period(d) and rng.random() < 0.6:
                discount = 0.15

            status = "completed"
            r = rng.random()
            if r < 0.021:
                status = "cancelled"

            lines = []
            for si in skus:
                sku = prod.sku[si]
                if ch == "ALG" and sku == STOCKOUT_SKU and d >= STOCKOUT_FROM:
                    # brak towaru na Allegro: część klientów wybiera mniejsze opakowanie, reszta odpada
                    if rng.random() < 0.35:
                        si = sku_idx["KRE-250"]
                    else:
                        continue
                qty = 1 if rng.random() > 0.14 else 2
                lines.append((si, qty))
            if not lines:
                continue

            has_acc = any(prod.category[si] == "Akcesoria" for si, _ in lines)
            if status == "completed" and rng.random() < (0.065 if has_acc else 0.028):
                status = "returned"

            for si, qty in lines:
                rows.append({
                    "order_id": oid, "ts": ts, "channel_code": ch, "customer_id": cid,
                    "sku": prod.sku[si], "product_name": prod.product_name[si],
                    "quantity": qty, "unit_price": prod.unit_price[si],
                    "discount_pct": int(discount * 100), "status": status,
                })

        # wydatki reklamowe dzienne (proporcjonalne do ruchu + szum, Meta podkręcona w listopadzie 2026)
        base = lam * 115
        meta_boost = 1.35 if d >= date(2026, 11, 2) else 1.0
        for platform, share in [("Meta Ads", 0.10 * meta_boost), ("Google Ads", 0.075),
                                ("Allegro Ads", 0.022), ("Amazon Ads", 0.012 + 0.03 * progress)]:
            ad_rows.append({"date": d.isoformat(), "platform": platform,
                            "spend_pln": round(base * share * rng.uniform(0.8, 1.2), 2),
                            "clicks": int(base * share * rng.uniform(0.8, 1.2) / 1.4)})

    df = pd.DataFrame(rows)

    # ---------- celowe zabrudzenie eksportu ----------
    df["order_date"] = df.ts.dt.strftime("%Y-%m-%d %H:%M:%S")
    mask_fmt = rng.random(len(df)) < 0.07
    df.loc[mask_fmt, "order_date"] = df.loc[mask_fmt, "ts"].dt.strftime("%d.%m.%Y %H:%M")

    ch_map = {"WWW": "Sklep WWW", "ALG": "Allegro", "AMZ": "Amazon.pl"}
    df["channel"] = df.channel_code.map(ch_map)
    noisy = rng.random(len(df))
    df.loc[noisy < 0.04, "channel"] = df.loc[noisy < 0.04, "channel"].str.lower()
    df.loc[(noisy >= 0.04) & (noisy < 0.06), "channel"] = " " + df.loc[(noisy >= 0.04) & (noisy < 0.06), "channel"] + " "
    df.loc[(noisy >= 0.06) & (noisy < 0.065), "channel"] = ""

    df["unit_price"] = df.unit_price.map(lambda v: f"{v:.2f}")
    alg_mask = df.channel_code == "ALG"
    df.loc[alg_mask, "unit_price"] = df.loc[alg_mask, "unit_price"].str.replace(".", ",", regex=False)

    ws = rng.random(len(df)) < 0.05
    df.loc[ws, "product_name"] = "  " + df.loc[ws, "product_name"] + " "

    # zamówienia testowe
    test_days = rng.choice(total_days, size=14, replace=False)
    tests = []
    for i, tdi in enumerate(test_days):
        td = START + timedelta(days=int(tdi))
        tests.append({"order_id": f"WWW-TEST{i:03d}", "order_date": f"{td.isoformat()} 10:0{i % 10}:00",
                      "channel": "Sklep WWW", "customer_id": "TEST", "sku": "WHY-900",
                      "product_name": "Białko Whey 900 g", "quantity": 1, "unit_price": "0.01",
                      "discount_pct": 0, "status": "test"})
    out_cols = ["order_id", "order_date", "channel", "customer_id", "sku", "product_name",
                "quantity", "unit_price", "discount_pct", "status"]
    df = pd.concat([df[out_cols], pd.DataFrame(tests)], ignore_index=True)

    # duplikaty (podwójny eksport z integracji)
    dup = df.sample(frac=0.012, random_state=SEED)
    df = pd.concat([df, dup], ignore_index=True).sample(frac=1, random_state=SEED).reset_index(drop=True)

    df.to_csv(DATA_RAW / "orders_raw.csv", index=False, encoding="utf-8")
    prod.drop(columns="popularity").to_csv(DATA_RAW / "products.csv", index=False, encoding="utf-8")
    pd.DataFrame(ad_rows).to_csv(DATA_RAW / "marketing_spend.csv", index=False, encoding="utf-8")

    print(f"orders_raw.csv: {len(df):,} wierszy | zamówień: {df.order_id.nunique():,} | klientów: {len(customers):,}")
    print(f"marketing_spend.csv: {len(ad_rows):,} wierszy | products.csv: {len(prod)} SKU")


if __name__ == "__main__":
    main()
