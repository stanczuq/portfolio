"""Zabezpieczenia wejścia i wyjścia.

Wejście: próby manipulacji modelem (prompt injection), nadmierna długość.
Wyjście: niedozwolone oświadczenia zdrowotne (suplementy diety nie mogą „leczyć”),
obietnice rekompensat bez decyzji człowieka, liczby i numery spoza kontekstu (halucynacje).
"""
import re

from .text import normalize

MAX_INPUT_CHARS = 4000

INJECTION = [
    r"zignoruj (wszystkie |poprzednie |wczesniejsze )?(instrukcj|polecen|zasad)", r"ignore (all |previous |prior )?instructions",
    r"system prompt", r"prompt systemow", r"jestes teraz", r"udawaj", r"tryb (dewelopera|developer)", r"\bjailbreak",
    r"wypisz (swoje|twoje) (instrukcj|zasad)", r"daj mi (kod rabatowy|rabat) 100",
]

HEALTH_CLAIMS = [
    r"\bleczy", r"wylecz", r"zapobiega\w* (chorob|nowotwor|cukrzyc)", r"gwarant\w* (efekt|rezultat|przyrost)",
    r"zastap\w* (lek|leczeni)", r"na raka", r"cudown", r"bezpieczn\w* w ciazy", r"mozesz (spokojnie )?(brac|stosowac) .*(ciaz|lek)",
    r"nie musisz (pytac|konsultowac) lekarz",
]

COMPENSATION = [r"rekompens", r"odszkodowan", r"gratis", r"w ramach przeprosin", r"(dodatkow|specjaln)\w* rabat", r"zwrocimy (cal|pel)"]


def check_input(message: str) -> tuple[str, list[str]]:
    flags = []
    if len(message) > MAX_INPUT_CHARS:
        message = message[:MAX_INPUT_CHARS]
        flags.append("wiadomość skrócona do 4000 znaków")
    t = normalize(message)
    if any(re.search(p, t) for p in INJECTION):
        flags.append("możliwa próba manipulacji asystentem (prompt injection)")
    return message, flags


def check_output(reply: str, context_text: str) -> list[str]:
    flags = []
    r = normalize(reply)
    if any(re.search(p, r) for p in HEALTH_CLAIMS):
        flags.append("niedozwolone oświadczenie zdrowotne w odpowiedzi")
    if any(re.search(p, r) for p in COMPENSATION):
        flags.append("obietnica rekompensaty wymaga decyzji konsultanta")
    ctx = normalize(context_text)
    unknown = [n for n in re.findall(r"\b[a-z]*\d{5,}\b", r) if n not in ctx]
    if unknown:
        flags.append(f"numer spoza kontekstu (możliwa halucynacja): {', '.join(unknown[:3])}")
    return flags
