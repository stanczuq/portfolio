"""Polityka trasowania: kto wysyła odpowiedź.

AUTO       odpowiedź wysyłana od razu (proste, informacyjne sprawy, pewna klasyfikacja)
DRAFT      szkic czeka na akceptację konsultanta (decyzje, zdrowie, niepewność, flagi bezpieczeństwa)
ESKALACJA  konsultant przejmuje sprawę od razu (zły klient, groźby prawne, zmiany w zamówieniu)

Reguły ustala biznes. AI pisze odpowiedź, ale to ta tabela decyduje, czy odpowiedź trafi do klienta bez człowieka.
"""

AUTO_INTENTS = {"status_zamowienia", "dostawa", "zwrot", "platnosc", "produkt", "dostepnosc"}
DRAFT_INTENTS = {"reklamacja", "zdrowie", "inne"}
ESCALATE_INTENTS = {"zmiana_zamowienia"}
MIN_CONFIDENCE = 0.6


def decide(intent: str, sentiment: str, confidence: float, legal_threat: bool,
           flags: list[str], order_lookup: dict | None) -> tuple[str, list[str]]:
    if legal_threat:
        return "ESKALACJA", ["groźba działań prawnych lub zgłoszenia do instytucji"]
    if sentiment == "zly":
        return "ESKALACJA", ["bardzo negatywny nastrój klienta"]
    if intent in ESCALATE_INTENTS:
        return "ESKALACJA", ["zmiana lub anulowanie zamówienia wymaga działania konsultanta przed wysyłką"]

    reasons = []
    if intent in DRAFT_INTENTS:
        reasons.append({"reklamacja": "reklamacja wymaga decyzji konsultanta",
                        "zdrowie": "pytanie zdrowotne: odpowiedź sprawdza człowiek",
                        "inne": "nierozpoznana intencja"}[intent])
    if confidence < MIN_CONFIDENCE and intent not in DRAFT_INTENTS:
        reasons.append(f"niska pewność klasyfikacji ({confidence:.2f})")
    if order_lookup and order_lookup.get("status") == "znaleziono" \
            and order_lookup["zamowienie"]["status"] == "wymaga potwierdzenia":
        reasons.append("zamówienie wstrzymane do weryfikacji: kontakt konsultanta")
    reasons += flags
    if reasons:
        return "DRAFT", reasons
    return "AUTO", [f"prosta sprawa informacyjna ({intent}), pewność {confidence:.2f}"]
