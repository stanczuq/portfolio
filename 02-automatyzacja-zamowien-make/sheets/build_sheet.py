"""Buduje sheets/VitaForge_Operacje.xlsx – szablon do importu w Google Sheets
(Plik › Importuj › Prześlij › „Zastąp arkusz kalkulacyjny”). Ponowne uruchomienie = reset magazynu."""
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulator"))
from catalog import load_products  # noqa: E402

HEAD_FILL = PatternFill("solid", fgColor="1F3A5F")
HEAD_FONT = Font(bold=True, color="FFFFFF")

TABS = {
    "Magazyn": ["sku", "nazwa", "kategoria", "cena", "vat", "stan", "prog_minimalny", "ilosc_zamawiana",
                "dostawca", "email_dostawcy", "status_zamowienia", "data_zamowienia", "do_zamowienia", "ostatnia_zmiana"],
    "Zamówienia": ["data", "nr", "shopify_id", "klient", "email", "wartosc", "platnosc", "dostawa", "pozycje",
                   "ryzyko_pkt", "status", "nr_faktury", "link_faktury", "nr_przesylki", "link_sledzenia"],
    "Do weryfikacji": ["data", "nr", "shopify_id", "klient", "email", "wartosc", "ryzyko_pkt", "powody",
                       "decyzja", "kto", "uwagi"],
    "Błędy": ["data", "nr", "shopify_id", "typ", "opis", "email"],
    "Zamówienia do dostawców": ["data", "dostawca", "email", "liczba_pozycji", "pozycje"],
}
WIDTHS = {"nazwa": 28, "dostawca": 20, "email_dostawcy": 32, "email": 32, "pozycje": 50, "powody": 45,
          "opis": 50, "link_faktury": 40, "link_sledzenia": 45, "klient": 22, "data": 18, "shopify_id": 17}


def header(ws, cols):
    ws.append(cols)
    for i, c in enumerate(cols, 1):
        cell = ws.cell(row=1, column=i)
        cell.fill, cell.font = HEAD_FILL, HEAD_FONT
        cell.alignment = Alignment(vertical="center")
        ws.column_dimensions[cell.column_letter].width = WIDTHS.get(c, max(12, len(c) + 2))
    ws.freeze_panes = "A2"


def main():
    wb = Workbook()
    wb.remove(wb.active)
    for name, cols in TABS.items():
        header(wb.create_sheet(name), cols)

    ws = wb["Magazyn"]
    products = load_products()
    for r, p in enumerate(products, start=2):
        ws.append([p["sku"], p["product_name"], p["category"], p["unit_price"], p["vat"], p["stock"],
                   p["min_level"], p["reorder_qty"], p["supplier"], p["supplier_email"], "", "",
                   f'=IF(AND(F{r}<=G{r},K{r}<>"zamówione"),"TAK","NIE")', ""])
    last = len(products) + 1
    red = PatternFill("solid", fgColor="F8D7DA")
    ws.conditional_formatting.add(f"A2:N{last}", FormulaRule(formula=[f"$F2<=$G2"], fill=red))

    dv = DataValidation(type="list", formula1='"Zatwierdź,Odrzuć"', allow_blank=True)
    wb["Do weryfikacji"].add_data_validation(dv)
    dv.add("I2:I500")

    out = ROOT / "sheets" / "VitaForge_Operacje.xlsx"
    wb.save(out)
    print(f"Zapisano {out.relative_to(ROOT)} ({len(products)} produktów)")


if __name__ == "__main__":
    main()
