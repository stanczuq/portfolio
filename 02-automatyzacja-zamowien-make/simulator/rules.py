"""Reguły biznesowe: walidacja i ocena ryzyka zamówienia.

To jest LUSTRO logiki zbudowanej w Make (scenariusz 1, moduł 2 „Walidacja i ryzyko”).
Symulator używa go, żeby dla każdego wysłanego zamówienia zapisać OCZEKIWANĄ trasę.
Po teście porównujesz ją z tym, co faktycznie zrobił Make (arkusz „Zamówienia”, „Błędy”,
„Do weryfikacji”). Zmieniasz próg tutaj, to zmieniasz go też w Make, i odwrotnie.
"""
import re

# --- Progi ryzyka (punkty sumują się) -------------------------------------
RISK_THRESHOLD = 50                 # >= tyle punktów: zamówienie wstrzymane do weryfikacji
HIGH_VALUE_PLN = 1500               # +30 pkt
NEW_CUSTOMER_HIGH_VALUE_PLN = 600   # +15 pkt, gdy pierwsze zamówienie klienta i wartość > tyle
COD_HIGH_VALUE_PLN = 800            # +15 pkt, płatność za pobraniem powyżej tej kwoty
MAX_QTY_SINGLE_ITEM = 10            # +20 pkt, >= tyle sztuk jednego produktu
DISPOSABLE_DOMAINS = [
    "mailinator.com", "yopmail.com", "10minutemail.com",
    "guerrillamail.com", "tempmail.com", "trashmail.com",
]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
ZIP_RE = re.compile(r"^\d{2}-\d{3}$")


def normalize_phone(phone: str | None) -> str:
    digits = re.sub(r"\D", "", phone or "")
    return re.sub(r"^48", "", digits) if len(digits) == 11 else digits


def validation_errors(order: dict) -> list[str]:
    errors = []
    email = (order.get("email") or "").strip()
    if not email:
        errors.append("brak e-maila")
    elif not EMAIL_RE.match(email):
        errors.append("nieprawidłowy e-mail")

    ship = order.get("shipping_address") or {}
    if not ZIP_RE.match(ship.get("zip") or ""):
        errors.append("nieprawidłowy kod pocztowy")
    if len(normalize_phone(ship.get("phone"))) != 9:
        errors.append("nieprawidłowy telefon")

    if not order.get("line_items"):
        errors.append("brak pozycji")

    code = (order.get("shipping_lines") or [{}])[0].get("code")
    locker = next((a["value"] for a in order.get("note_attributes", []) if a["name"] == "paczkomat"), "")
    if code == "inpost_locker" and not locker:
        errors.append("brak paczkomatu")
    return errors


def risk(order: dict) -> tuple[int, list[str]]:
    score, reasons = 0, []
    value = float(order["total_price"])
    email = (order.get("email") or "").lower()
    first_order = order.get("customer", {}).get("orders_count", 0) <= 1
    bill_city = (order.get("billing_address") or {}).get("city", "").lower()
    ship_city = (order.get("shipping_address") or {}).get("city", "").lower()
    max_qty = max((li["quantity"] for li in order.get("line_items", [])), default=0)

    if value > HIGH_VALUE_PLN:
        score += 30; reasons.append("wysoka wartość")
    if first_order and value > NEW_CUSTOMER_HIGH_VALUE_PLN:
        score += 15; reasons.append("nowy klient z dużym koszykiem")
    if email.split("@")[-1] in DISPOSABLE_DOMAINS:
        score += 30; reasons.append("jednorazowy e-mail")
    if bill_city and ship_city and bill_city != ship_city:
        score += 25; reasons.append("różne miasto faktury i dostawy")
    if max_qty >= MAX_QTY_SINGLE_ITEM:
        score += 20; reasons.append("duża ilość jednego produktu")
    if order.get("gateway") == "cash_on_delivery" and value > COD_HIGH_VALUE_PLN:
        score += 15; reasons.append("pobranie przy wysokiej kwocie")
    return score, reasons


def expected_route(order: dict, stock: dict[str, int], seen_ids: set) -> str:
    """Trasa, którą powinien wybrać router w Make."""
    if order["id"] in seen_ids:
        return "A: duplikat"
    if validation_errors(order):
        return "B: błędne dane"
    if risk(order)[0] >= RISK_THRESHOLD:
        return "C: do weryfikacji"
    if any(stock.get(li["sku"], 0) < li["quantity"] for li in order["line_items"]):
        return "D1: brak towaru"
    return "D2: realizacja"
