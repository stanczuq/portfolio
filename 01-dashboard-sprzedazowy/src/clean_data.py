"""
Etap 1 pipeline'u: czyszczenie surowego eksportu zamówień.

Wejście:  data/raw/orders_raw.csv, data/raw/products.csv, data/raw/marketing_spend.csv
Wyjście:  data/processed/orders_clean.csv   – jedna pozycja zamówienia na wiersz, z kosztami i marżą
          data/processed/marketing_clean.csv
          data/processed/data_quality_report.md – co zostało poprawione i ile wierszy
"""
from datetime import datetime

import pandas as pd

from config import AD_PLATFORM_CHANNEL, CHANNEL_FEE, CHANNELS, DATA_PROCESSED, DATA_RAW


def parse_date(value: str) -> pd.Timestamp:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M", "%Y-%m-%d %H:%M"):
        try:
            return pd.Timestamp(datetime.strptime(value.strip(), fmt))
        except ValueError:
            continue
    return pd.NaT


def normalize_channel(raw: str, order_id: str) -> str:
    """Ujednolica nazwę kanału; brakującą odtwarza z prefiksu numeru zamówienia."""
    lookup = {v.lower(): v for v in CHANNELS.values()}
    key = str(raw).strip().lower() if isinstance(raw, str) else ""
    if key in lookup:
        return lookup[key]
    return CHANNELS.get(order_id.split("-")[0], "Nieznany")


def main() -> dict:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(DATA_RAW / "orders_raw.csv", dtype=str, keep_default_na=False)
    products = pd.read_csv(DATA_RAW / "products.csv")
    log: list[tuple[str, int]] = []
    n0 = len(raw)

    # 1. duplikaty – identyczne wiersze z podwójnego eksportu
    df = raw.drop_duplicates()
    log.append(("Usunięte zduplikowane wiersze (podwójny eksport)", n0 - len(df)))

    # 2. zamówienia testowe
    test_mask = (df.status == "test") | (df.customer_id == "TEST") | df.order_id.str.contains("TEST")
    log.append(("Usunięte zamówienia testowe", int(test_mask.sum())))
    df = df[~test_mask]

    # 3. anulowane – nie są sprzedażą
    canc = df.status == "cancelled"
    log.append(("Pominięte pozycje zamówień anulowanych", int(canc.sum())))
    df = df[~canc].copy()

    # 4. daty w różnych formatach
    non_iso = (~df.order_date.str.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")).sum()
    df["order_ts"] = df.order_date.map(parse_date)
    log.append(("Ujednolicone daty w formacie DD.MM.RRRR", int(non_iso)))
    bad_dates = df.order_ts.isna().sum()
    df = df[df.order_ts.notna()]
    log.append(("Usunięte wiersze z nieczytelną datą", int(bad_dates)))

    # 5. kanał sprzedaży
    canonical = set(CHANNELS.values())
    fixed_ch = (~df.channel.isin(canonical)).sum()
    missing_ch = (df.channel.str.strip() == "").sum()
    df["channel"] = [normalize_channel(c, o) for c, o in zip(df.channel, df.order_id)]
    log.append(("Ujednolicone nazwy kanałów (wielkość liter, spacje)", int(fixed_ch - missing_ch)))
    log.append(("Odtworzony brakujący kanał z numeru zamówienia", int(missing_ch)))

    # 6. liczby: przecinek dziesiętny, typy
    comma = df.unit_price.str.contains(",").sum()
    df["unit_price"] = df.unit_price.str.replace(",", ".", regex=False).astype(float)
    df["quantity"] = df.quantity.astype(int)
    df["discount_pct"] = df.discount_pct.astype(float)
    df["customer_id"] = df.customer_id.astype(int)
    log.append(("Poprawione ceny z przecinkiem dziesiętnym", int(comma)))

    # 7. nazwy produktów – białe znaki; źródłem prawdy jest katalog po SKU
    ws = (df.product_name != df.product_name.str.strip()).sum()
    df = df.drop(columns="product_name").merge(products, on="sku", how="left", suffixes=("", "_catalog"))
    log.append(("Oczyszczone nazwy produktów (białe znaki)", int(ws)))
    unknown = df.category.isna().sum()
    df = df[df.category.notna()]
    log.append(("Usunięte pozycje z nieznanym SKU", int(unknown)))

    # 8. wyliczenia finansowe (kwoty netto)
    df["revenue"] = (df.quantity * df.unit_price * (1 - df.discount_pct / 100)).round(2)
    df["cogs"] = (df.quantity * df.unit_cost).round(2)
    df["channel_fee"] = (df.revenue * df.channel.map(CHANNEL_FEE)).round(2)
    df["is_returned"] = (df.status == "returned").astype(int)
    df["gross_margin"] = (df.revenue - df.cogs - df.channel_fee).round(2)

    # nowy vs powracający klient – pierwsze zamówienie klienta w historii
    first = df.groupby("customer_id").order_ts.min().rename("first_order_ts")
    df = df.merge(first, on="customer_id")
    df["is_new_customer"] = (df.order_ts == df.first_order_ts).astype(int)

    df["date"] = df.order_ts.dt.date
    df["hour"] = df.order_ts.dt.hour
    df["iso_week"] = df.order_ts.dt.strftime("%G-W%V")

    cols = ["order_id", "order_ts", "date", "iso_week", "hour", "channel", "customer_id", "is_new_customer",
            "sku", "product_name", "category", "quantity", "unit_price", "discount_pct",
            "revenue", "cogs", "channel_fee", "gross_margin", "status", "is_returned"]
    df = df[cols].sort_values(["order_ts", "order_id"]).reset_index(drop=True)
    df.to_csv(DATA_PROCESSED / "orders_clean.csv", index=False, encoding="utf-8")

    mk = pd.read_csv(DATA_RAW / "marketing_spend.csv")
    mk["channel"] = mk.platform.map(AD_PLATFORM_CHANNEL)
    mk["date"] = pd.to_datetime(mk.date)
    mk["iso_week"] = mk.date.dt.strftime("%G-W%V")
    mk.to_csv(DATA_PROCESSED / "marketing_clean.csv", index=False, encoding="utf-8")

    # raport jakości danych
    lines = ["# Raport jakości danych", "",
             f"Wygenerowano: {datetime.now():%Y-%m-%d %H:%M}", "",
             f"- Wiersze w surowym eksporcie: **{n0:,}**".replace(",", " "),
             f"- Wiersze po czyszczeniu: **{len(df):,}**".replace(",", " "),
             f"- Zamówienia po czyszczeniu: **{df.order_id.nunique():,}**".replace(",", " "),
             f"- Zakres dat: {df.order_ts.min():%Y-%m-%d} – {df.order_ts.max():%Y-%m-%d}", "",
             "| Krok czyszczenia | Liczba wierszy |", "|---|---:|"]
    lines += [f"| {name} | {cnt:,} |".replace(f"{cnt:,}", f"{cnt:,}".replace(",", " ")) for name, cnt in log]
    (DATA_PROCESSED / "data_quality_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(f"  {n}: {c}" for n, c in log))
    print(f"orders_clean.csv: {len(df):,} pozycji, {df.order_id.nunique():,} zamówień")
    return {"raw_rows": n0, "clean_rows": len(df)}


if __name__ == "__main__":
    main()
