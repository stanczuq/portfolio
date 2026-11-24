"""Orkiestracja: jedna wiadomość klienta -> odpowiedź + decyzja, kto ją wysyła.

    wejście ─► zabezpieczenia wejścia ─► klasyfikacja (intencja, nastrój, pewność)
           ─► narzędzia (zamówienie z weryfikacją e-maila, produkty i stany) + baza wiedzy (BM25)
           ─► odpowiedź (Claude albo szablony) ─► zabezpieczenia wyjścia ─► polityka: AUTO / DRAFT / ESKALACJA ─► log

To celowo „workflow”, a nie autonomiczny agent: kolejność kroków jest stała, model nie decyduje,
które narzędzia wywołać ani czy wysłać odpowiedź. Dzięki temu zachowanie jest przewidywalne i testowalne.
"""
import json
import time
from datetime import datetime

from . import config, guardrails, policy
from .knowledge_base import KnowledgeBase
from .llm import ClaudeLLM, OfflineLLM
from .store import Store
from .text import extract_email, extract_order_number, mask_pii

# Dopowiedzenie do zapytania BM25 zależne od intencji: krótkie pytania („a w ciąży?”) też trafią we właściwy fragment.
INTENT_HINTS = {
    "status_zamowienia": "statusy zamówienia",
    "zdrowie": "bezpieczeństwo stosowania lekarz",
    "zwrot": "zwrot",
    "reklamacja": "reklamacja",
    "zmiana_zamowienia": "anulowanie zmiana zamówienia",
    "dostepnosc": "",
}
INTENT_DOCS = {
    "status_zamowienia": ["zamowienia", "dostawa"], "dostawa": ["dostawa"], "zwrot": ["zwroty"],
    "reklamacja": ["reklamacje"], "platnosc": ["platnosci"], "produkt": ["produkty"],
    "dostepnosc": ["produkty"], "zmiana_zamowienia": ["zamowienia"], "zdrowie": ["produkty"],
}
ROUTE_HINTS = {
    "AUTO": "Odpowiedź zostanie wysłana automatycznie.",
    "DRAFT": "To szkic do akceptacji konsultanta.",
    "ESKALACJA": "Sprawę przejmuje konsultant: napisz krótkie potwierdzenie przyjęcia zgłoszenia.",
}


class Assistant:
    def __init__(self, mode: str | None = None, log: bool = True):
        self.kb = KnowledgeBase(config.KNOWLEDGE_DIR)
        self.store = Store(config.DATA_DIR)
        mode = mode or config.MODE
        self.llm = ClaudeLLM(config.MODEL) if mode == "claude" else OfflineLLM()
        self.mode, self.log = mode, log

    def handle(self, message: str, sender_email: str | None = None, history: list[dict] | None = None,
               channel: str = "chat") -> dict:
        t0 = time.perf_counter()
        message, in_flags = guardrails.check_input(message)
        earlier = " ".join(m["content"] for m in (history or []) if m.get("role") == "user")

        order_number = extract_order_number(message) or extract_order_number(earlier)
        email = (sender_email or extract_email(message) or "").lower() or None

        cls, u1 = self.llm.classify(message if not earlier else f"{earlier}\n{message}", bool(order_number))
        intent = cls["intent"]

        order_lookup = None
        if intent in ("status_zamowienia", "zmiana_zamowienia", "reklamacja", "zwrot") or order_number:
            order_lookup = self.store.lookup_order(order_number, email)
        products = [{"sku": p.sku, "nazwa": p.name, "cena": p.price, "dostepny": p.available,
                     "dostawa_planowana": p.restock_date} for p in self.store.find_products(message)]
        hits = self.kb.search(f"{message} {INTENT_HINTS.get(intent, '')}", k=3, prefer_docs=INTENT_DOCS.get(intent), boost=2.0)
        kb = [{"id": c.id, "title": c.title, "text": c.text, "score": s} for c, s in hits]

        ctx = {"order_number": order_number, "order_lookup": order_lookup, "products": products, "kb": kb}
        ctx["context_text"] = self._context_text(ctx)

        # Wstępna trasa (bez flag wyjścia) trafia do promptu, żeby styl pasował do sytuacji.
        pre_route, _ = policy.decide(intent, cls["sentiment"], cls["confidence"], cls["legal_threat"], in_flags, order_lookup)
        reply, u2 = self.llm.generate(message, ctx, cls, ROUTE_HINTS[pre_route])

        out_flags = guardrails.check_output(reply, ctx["context_text"] + " " + message)
        route, reasons = policy.decide(intent, cls["sentiment"], cls["confidence"], cls["legal_threat"],
                                       in_flags + out_flags, order_lookup)
        result = {
            "intent": intent, "sentiment": cls["sentiment"], "confidence": round(cls["confidence"], 2),
            "route": route, "reasons": reasons, "reply": reply.strip(),
            "sources": [k["id"] for k in kb], "order_lookup": (order_lookup or {}).get("status"),
            "products": [p["sku"] for p in products], "flags": in_flags + out_flags,
            "engine": self.llm.name, "latency_ms": int((time.perf_counter() - t0) * 1000),
            "tokens": {k: u1.get(k, 0) + u2.get(k, 0) for k in ("input_tokens", "output_tokens")},
        }
        if self.log:
            self._log(message, channel, result)
        return result

    @staticmethod
    def _context_text(ctx: dict) -> str:
        lines = ["BAZA WIEDZY:"] + [f"[{k['id']}] {k['title']}: {k['text']}" for k in ctx["kb"]]
        ol = ctx["order_lookup"]
        if ol:
            lines.append("\nZAMÓWIENIE:")
            if ol["status"] == "znaleziono":
                o = dict(ol["zamowienie"]); o.pop("email", None)
                lines.append(json.dumps(o, ensure_ascii=False))
            else:
                lines.append({"brak_numeru": "Klient nie podał numeru zamówienia.",
                              "nie_znaleziono": f"Brak zamówienia o numerze {ol.get('numer')}.",
                              "email_niezgodny": f"Zamówienie {ol.get('numer')} istnieje, ale e-mail nadawcy NIE zgadza się z e-mailem zamówienia. Nie ujawniaj szczegółów."}[ol["status"]])
        if ctx["products"]:
            lines.append("\nPRODUKTY (stan magazynu na teraz):")
            for p in ctx["products"]:
                stan = "dostępny" if p["dostepny"] else f"niedostępny, planowana dostawa: {p['dostawa_planowana'] or 'brak terminu'}"
                lines.append(f"- {p['nazwa']} ({p['sku']}): {p['cena']:.2f} zł, {stan}")
        return "\n".join(lines)

    def _log(self, message: str, channel: str, r: dict) -> None:
        config.LOG_FILE.parent.mkdir(exist_ok=True)
        entry = {"czas": datetime.now().isoformat(timespec="seconds"), "kanal": channel, "wiadomosc": mask_pii(message),
                 **{k: r[k] for k in ("intent", "sentiment", "confidence", "route", "reasons", "sources", "latency_ms", "tokens")}}
        with open(config.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
