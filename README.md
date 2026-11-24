# Portfolio · Patryk Stańczuk

**Automatyzacja procesów i AI w e-commerce.** Trzy połączone projekty dla jednego (fikcyjnego) sklepu z suplementami **VitaForge**.

🌐 **Strona portfolio z demami na żywo: https://stanczuq.github.io/portfolio/**

| # | Projekt | Pytanie biznesowe | Stack | Demo |
|---|---|---|---|---|
| 01 | [Dashboard sprzedażowy z raportem tygodniowym](01-dashboard-sprzedazowy) | Co się dzieje w sprzedaży w 3 kanałach i co z tym zrobić? | Python, pandas, HTML/SVG, Make, GitHub Actions | [dashboard](https://stanczuq.github.io/portfolio/01-dashboard-sprzedazowy/dashboard/) |
| 02 | [Automatyzacja zamówień w Make](02-automatyzacja-zamowien-make) | Jak obsłużyć każde zamówienie od webhooka do paczki bez ręcznej pracy? | Make, REST API, Google Sheets, Gmail, Slack, Python | [opis i blueprinty](02-automatyzacja-zamowien-make) |
| 03 | [Asystent AI obsługi klienta](03-asystent-ai-obslugi-klienta) | Jak odpowiadać klientom od razu, ale bez ryzyka? | Claude API, RAG, guardrails, ewaluacja, FastAPI, Make | [czat](https://stanczuq.github.io/portfolio/03-asystent-ai-obslugi-klienta/web/) |

Projekty korzystają z tych samych danych: ten sam katalog produktów, wyprzedana kreatyna `KRE-500`, która w projekcie 1 wywołuje alert spadku Allegro,
w projekcie 2 kieruje zamówienie na trasę „brak towaru”, a w projekcie 3 asystent odpowiada klientowi, kiedy wróci na stan.

## Uruchomienie lokalne

**Windows:** kliknij dwa razy `START.bat` i wybierz numer z menu. Przy pierwszym uruchomieniu skrypt sam utworzy środowisko Pythona i zainstaluje biblioteki.

**macOS / Linux:**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd 01-dashboard-sprzedazowy && python run_all.py --skip-generate          # projekt 1
cd 02-automatyzacja-zamowien-make && python simulator/send_orders.py      # projekt 2 (podgląd)
cd 03-asystent-ai-obslugi-klienta && uvicorn api.server:app --port 8000   # projekt 3: http://localhost:8000
```

Wymagany Python 3.10+. Szczegóły w README każdego projektu.

---

**Patryk Stańczuk** · [github.com/Stanczuq](https://github.com/Stanczuq) · Make Foundation L1–L3 · studia: AI w biznesie

<sub>English: three connected portfolio projects for a fictional e-commerce store: a sales dashboard with an automated weekly report, end-to-end order automation in Make, and an AI customer-service assistant with guardrails and evaluation. Each project's README ends with an English summary.</sub>
