"""Dwa „silniki” z tym samym interfejsem:

ClaudeLLM   klasyfikacja i odpowiedź przez Claude API (Anthropic)
OfflineLLM  reguły + szablony z fragmentów bazy wiedzy; działa bez klucza, służy do demo i jako baseline w ewaluacji

Orkiestracja (co pobrać, kto wysyła) jest w assistant.py i nie zależy od silnika.
"""
import json
import re

from . import prompts, rules
from .text import tokens

STATUS_TEMPLATES = {
    "przyjęte": "Twoje zamówienie #{numer} z {data} zostało przyjęte. Zamówienia opłacone do 14:00 w dni robocze wysyłamy tego samego dnia, a numer przesyłki dostaniesz mailem razem z fakturą.",
    "w realizacji": "Twoje zamówienie #{numer} z {data} jest w realizacji, właśnie kompletujemy paczkę. Numer przesyłki dostaniesz mailem razem z fakturą, gdy tylko paczka zostanie nadana ({metoda_dostawy}).",
    "wysłane": "Twoje zamówienie #{numer} zostało wysłane ({metoda_dostawy}). Numer przesyłki: {numer_przesylki}. Doręczenie trwa zwykle 1–2 dni robocze od nadania.",
    "doręczone": "Według przewoźnika zamówienie #{numer} zostało doręczone (numer przesyłki {numer_przesylki}). Jeśli paczki nie masz, odpisz na tę wiadomość, a złożymy reklamację u przewoźnika.",
    "oczekuje na towar": "Twoje zamówienie #{numer} czeka na produkt: {braki}. Planowana dostawa do magazynu: {dostawa}. Całe zamówienie wyślemy zaraz potem. Jeśli wolisz dostać resztę wcześniej albo zamienić produkt, odpisz, a konsultant to przygotuje.",
    "wymaga potwierdzenia": "Twoje zamówienie #{numer} wymaga dodatkowego potwierdzenia przed wysyłką. Konsultant skontaktuje się z Tobą w godzinach 8:00–16:00 w dzień roboczy.",
}


def _parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}


_ABBR = re.compile(r"\b(szt|kaps|np|ul|art|ok|tj|nr)\.")


def _sentences(text: str) -> list[str]:
    """Dzieli na zdania, nie rozcinając skrótów („240 szt.”, „ul. Magazynowa”)."""
    protected = _ABBR.sub(lambda m: m.group(1) + "\u00a7", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-ZŁŚŻŹĆĄĘÓŃ„\"])", protected)
    return [p.replace("\u00a7", ".").strip() for p in parts if p.strip()]


class OfflineLLM:
    name = "offline (reguły + szablony)"

    def classify(self, message: str, has_order_number: bool) -> tuple[dict, dict]:
        return rules.classify(message, has_order_number), {"input_tokens": 0, "output_tokens": 0}

    def generate(self, message: str, ctx: dict, cls: dict, route_hint: str) -> tuple[str, dict]:
        intent, parts = cls["intent"], []
        order = ctx.get("order_lookup") or {}
        name = order.get("zamowienie", {}).get("imie") if order.get("status") == "znaleziono" else None
        greeting = f"Cześć {name}!" if name else "Cześć!"
        if cls["sentiment"] in ("negatywny", "zly"):
            parts.append("Bardzo przepraszamy za kłopot.")

        if intent == "status_zamowienia":
            parts.append(self._order_text(order))
        elif intent == "zdrowie":
            parts.append("Dziękujemy za pytanie. Nie udzielamy porad medycznych, dlatego stosowanie suplementów w Twojej sytuacji "
                         "skonsultuj z lekarzem lub farmaceutą. Nie przekraczaj porcji zalecanej na etykiecie.")
            if ctx["products"]:
                parts.append(f"Chętnie wyślemy pełny skład z etykiety produktu {ctx['products'][0]['nazwa']}, żeby łatwiej było go omówić z lekarzem.")
        elif intent == "zmiana_zamowienia":
            parts.append("Przekazaliśmy Twoją prośbę konsultantowi. Zamówienie można zmienić lub anulować do momentu wysyłki, "
                         "a konsultant potwierdzi zmianę mailem w godzinach 8:00–16:00.")
            if order.get("status") == "znaleziono" and order["zamowienie"]["status"] in ("wysłane", "doręczone"):
                parts.append("Ta paczka jest już nadana, więc adres zmienisz przez przekierowanie w aplikacji InPost Mobile.")
            elif not ctx.get("order_number"):
                parts.append("Podaj proszę numer zamówienia, żeby przyspieszyć sprawę.")
        else:
            if intent != "dostepnosc" or not ctx["products"]:
                parts += self._kb_sentences(message, ctx["kb"])
            if intent in ("dostepnosc", "produkt"):
                parts += [self._product_line(p) for p in ctx["products"] if intent == "dostepnosc" or not p["dostepny"]]
            if intent == "dostepnosc" and not ctx["products"]:
                parts.append("Napisz proszę, o który produkt chodzi, a sprawdzimy stan magazynu.")
            if intent == "reklamacja":
                parts.append("Zgłoszenie przekazaliśmy konsultantowi, który poprowadzi reklamację.")
            if intent == "inne" or not parts:
                parts.append("Dziękujemy za wiadomość. Przekazaliśmy ją konsultantowi, który odpowie w ciągu 1 dnia roboczego.")

        reply = greeting + "\n\n" + " ".join(p for p in parts if p) + "\n\nPozdrawiamy,\nZespół VitaForge"
        return reply, {"input_tokens": 0, "output_tokens": 0}

    @staticmethod
    def _order_text(order: dict) -> str:
        st = order.get("status")
        if st == "brak_numeru":
            return ("Podaj proszę numer zamówienia (znajdziesz go w mailu z potwierdzeniem, zaczyna się od #) i napisz z adresu e-mail "
                    "użytego przy zamówieniu, a od razu sprawdzimy status.")
        if st == "nie_znaleziono":
            return (f"Nie znaleźliśmy zamówienia o numerze #{order['numer']}. Sprawdź proszę numer w mailu z potwierdzeniem "
                    "i odpisz z adresu e-mail użytego przy zamówieniu.")
        if st == "email_niezgodny":
            return (f"Ze względów bezpieczeństwa szczegóły zamówienia #{order['numer']} podajemy tylko w odpowiedzi na wiadomość "
                    "z adresu e-mail użytego przy zamówieniu. Napisz proszę z tego adresu, a od razu sprawdzimy status.")
        o = order["zamowienie"]
        missing = [p for p in o["pozycje"] if p["brak"]]
        return STATUS_TEMPLATES[o["status"]].format(
            **o, braki=", ".join(p["produkt"] for p in missing) or "-",
            dostawa=next((p["dostawa_planowana"] for p in missing if p["dostawa_planowana"]), "konsultant poda termin"))

    @staticmethod
    def _product_line(p: dict) -> str:
        if p["dostepny"]:
            return f"Produkt {p['nazwa']} ({p['cena']:.2f} zł) jest dostępny i możemy go wysłać od razu."
        when = f"Planowana dostawa: {p['dostawa_planowana']}." if p["dostawa_planowana"] else "Termin dostawy poda konsultant."
        return f"Produkt {p['nazwa']} jest chwilowo niedostępny. {when}"

    @staticmethod
    def _kb_sentences(message: str, kb: list[dict], n: int = 3) -> list[str]:
        """Wybiera z najlepszych fragmentów zdania najbardziej pokrywające się z pytaniem."""
        q = set(tokens(message))
        cands = []
        same_doc = [ch for ch in kb if kb and ch["id"].split("#")[0] == kb[0]["id"].split("#")[0]]
        for rank, ch in enumerate(same_doc[:2]):
            for pos, s in enumerate(_sentences(ch["text"])):
                overlap = len(q & set(tokens(s)))
                cands.append((overlap * (1.0 if rank == 0 else 0.6) + (0.5 if pos == 0 and rank == 0 else 0), rank, pos, s))
        best = sorted(sorted(cands, key=lambda x: -x[0])[:n], key=lambda x: (x[1], x[2]))
        return [s for score, _, _, s in best if score > 0]


class ClaudeLLM:
    def __init__(self, model: str, max_tokens: int = 600):
        import anthropic  # import tylko w trybie online
        self.client = anthropic.Anthropic()
        self.model, self.max_tokens = model, max_tokens
        self.name = f"Claude ({model})"

    def _call(self, system: str, user: str, max_tokens: int) -> tuple[str, dict]:
        r = self.client.messages.create(model=self.model, max_tokens=max_tokens, system=system,
                                        messages=[{"role": "user", "content": user}])
        text = "".join(b.text for b in r.content if b.type == "text")
        return text, {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens}

    def classify(self, message: str, has_order_number: bool) -> tuple[dict, dict]:
        text, usage = self._call(prompts.CLASSIFY_SYSTEM, f"<wiadomosc_klienta>\n{message}\n</wiadomosc_klienta>", 200)
        base = rules.classify(message, has_order_number)      # reguły zostają jako siatka bezpieczeństwa
        try:
            data = _parse_json(text)
        except json.JSONDecodeError:
            data = {}
        intent = data.get("intent") if data.get("intent") in rules.INTENTS else base["intent"]
        if base["intent"] == "zdrowie":                       # zdrowie wykryte regułą nigdy nie jest „przegłosowane”
            intent = "zdrowie"
        return {
            "intent": intent,
            "sentiment": data.get("sentiment", base["sentiment"]),
            "confidence": float(data.get("confidence", base["confidence"])),
            "legal_threat": base["legal_threat"],
            "summary": data.get("summary", ""),
        }, usage

    def generate(self, message: str, ctx: dict, cls: dict, route_hint: str) -> tuple[str, dict]:
        return self._call(prompts.REPLY_SYSTEM,
                          prompts.reply_user_prompt(message, ctx["context_text"], cls["intent"], route_hint), self.max_tokens)
