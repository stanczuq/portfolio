"""Klasyfikacja regułowa: intencja i nastrój wiadomości.

Używana w trybie offline (bez klucza API) i jako punkt odniesienia w ewaluacji:
pokazuje, ile daje model językowy ponad proste słowa kluczowe.
"""
import re

from .text import normalize

INTENTS = [
    "status_zamowienia", "dostawa", "zwrot", "reklamacja", "platnosc",
    "produkt", "dostepnosc", "zmiana_zamowienia", "zdrowie", "inne",
]

PATTERNS = {
    "status_zamowienia": [r"gdzie (jest )?(moj|moja|moje|paczk|zamowien|przesyl)", r"\bstatus", r"kiedy (dotrze|przyjdzie|bedzie moj|dostane|wyslecie)",
                          r"nie (doszl|dotarl|przyszl)", r"sledz", r"numer (przesylki|sledzenia)", r"jeszcze nie (mam|dostal)",
                          r"czy (juz )?(wyslal|wyszl|nadal)", r"co sie dzieje z"],
    "dostawa": [r"koszt\w* (dostaw|wysyl)", r"ile kosztuje (dostawa|wysylka)", r"darmow\w* (dostaw|wysyl)", r"(dostaw|wysyl)\w* (jest )?darmow",
                r"czas\w* (dostaw|wysyl|realizac)", r"paczkomat", r"kurier", r"za granic", r"wysylacie", r"do (niemiec|czech|anglii|holandii|norwegii)",
                r"ile (trwa|sie czeka)", r"wysl\w*( \w+)? (dzis|dzisiaj|jutro)", r"(zamowie|zamowic|zaplace)( \w+)? do \d", r"(zamowie|zamowic) (do|przed) \d"],
    "zwrot": [r"zwro[ct]", r"oddac", r"odstapi", r"odeslac"],
    "reklamacja": [r"reklamac", r"uszkodz", r"zniszcz", r"rozbit", r"pekniet", r"pekl", r"wadliw", r"zly produkt", r"inny produkt niz",
                   r"brakuje", r"zepsut", r"przeterminowan", r"zbryl", r"dziwn\w* (smak|zapach)", r"otwart\w* (opakowan|wieczk)"],
    "platnosc": [r"platn", r"zaplac", r"\bblik", r"paypo", r"faktur", r"\bnip\b", r"kod\w* (rabatow|promocyj)", r"rabat", r"przelew", r"\bkart[aey]\b"],
    "produkt": [r"(jaki|jaka|jakie|ktory|ktora|ktore)\b.*(wybrac|polecacie|lepsz|dla mnie)", r"polec", r"smak", r"sklad", r"porcj", r"roznic",
                r"wegan", r"laktoz", r"gluten", r"waznosc", r"przechowyw", r"certyfikat", r"rozmiar", r"czym sie rozni", r"zawiera"],
    "dostepnosc": [r"dostepn", r"kiedy (bedzie|wroci|pojawi)", r"na stan", r"wyprzedan", r"brak (na stanie|towaru)", r"powiadom", r"wroci do sprzedazy"],
    "zmiana_zamowienia": [r"anul", r"zmieni\w* (adres|paczkomat|zamowien|produkt|smak|rozmiar)", r"zmiana (adresu|zamowienia|paczkomatu)",
                          r"dodac do (zamowienia|paczki)", r"pomylil\w* (sie )?(w|przy) (adres|zamowien)", r"rezygnuj"],
    "zdrowie": [r"\bciaz", r"karmi\w* piersi", r"karmie", r"\blek(i|ow|ami|u)?\b", r"chorob", r"cukrzyc", r"nadcisnien", r"cisnien",
                r"tarczyc", r"hashimoto", r"nerk", r"watrob", r"\bserc", r"lekarz", r"operac", r"\bsyn\w*\b.*\b1[0-7]\b", r"\b1[0-7] lat",
                r"alergi", r"(skutki|efekty) uboczne", r"antybiotyk", r"antykoncepc", r"depresj", r"leczy", r"wylecz"],
}

# Priorytet bezpieczeństwa: pytanie zdrowotne wygrywa nawet z silniejszym dopasowaniem do produktu.
PRIORITY = ["zdrowie", "zmiana_zamowienia", "reklamacja"]

ANGRY = [r"skandal", r"zenad", r"oszus", r"kpin", r"nigdy wiecej", r"uokik", r"rzecznik\w* (praw )?konsument", r"prawnik", r"\bsad\w*\b",
         r"pozew", r"chargeback", r"!!!", r"wkurz", r"tragedi", r"beznadziej", r"zlodziej", r"zartuj", r"ostatni raz", r"zglosze .* (policj|uokik)"]
NEGATIVE = [r"niestety", r"rozczar", r"problem", r"opozni", r"nadal nie", r"wciaz nie", r"juz \d+ dni", r"czekam", r"nie dziala", r"zawiod"]
POSITIVE = [r"dziekuj", r"super", r"swietn", r"polecam", r"zadowolon", r"rewelac"]

LEGAL_THREAT = [r"uokik", r"rzecznik", r"prawnik", r"\bsad\w*\b", r"pozew", r"chargeback", r"policj"]


def _count(patterns: list[str], text: str) -> int:
    return sum(1 for p in patterns if re.search(p, text))


def classify(message: str, has_order_number: bool = False) -> dict:
    t = normalize(message)
    scores = {i: _count(PATTERNS[i], t) for i in PATTERNS}
    if has_order_number and (scores["status_zamowienia"] or scores["dostawa"]):
        scores["status_zamowienia"] += 1

    intent = next((i for i in PRIORITY if scores[i] > 0), None)
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    if intent is None:
        intent = ranked[0][0] if ranked[0][1] > 0 else "inne"
    top = scores.get(intent, 0)
    second = max((s for i, s in scores.items() if i != intent), default=0)
    confidence = 0.3 if intent == "inne" else (0.9 if top - second >= 2 else 0.75 if top > second else 0.6)

    if _count(ANGRY, t) or len(re.findall(r"[A-ZŁŚŻŹĆĄĘÓŃ]{5,}", message)) >= 2:
        sentiment = "zly"
    elif _count(NEGATIVE, t):
        sentiment = "negatywny"
    elif _count(POSITIVE, t):
        sentiment = "pozytywny"
    else:
        sentiment = "neutralny"

    return {"intent": intent, "sentiment": sentiment, "confidence": confidence,
            "legal_threat": bool(_count(LEGAL_THREAT, t)), "scores": {k: v for k, v in scores.items() if v}}
