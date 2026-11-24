"""Ewaluacja asystenta na 30 przypadkach z oczekiwanym wynikiem.

Mierzy osobno każdą warstwę, żeby było wiadomo, CO poprawiać:
  intencja    czy klasyfikator rozpoznał sprawę
  trasa       czy polityka wybrała AUTO / DRAFT / ESKALACJA zgodnie z oczekiwaniem
  źródło      czy wyszukiwanie znalazło właściwy fragment bazy wiedzy (w top 3)
  fakty       czy odpowiedź zawiera wymagane informacje (np. „12,99”, numer przesyłki)
  zakazane    czy odpowiedź NIE zawiera tego, czego nie wolno (np. numeru przesyłki dla obcej osoby)

Najważniejsza metryka biznesowa: „niebezpieczne AUTO”, czyli sprawy, które powinny trafić do człowieka,
a zostały wysłane automatycznie. Ta liczba musi wynosić 0.

    python eval/run_eval.py                 # tryb z .env (claude, jeśli jest klucz)
    python eval/run_eval.py --mode offline  # bez API
"""
import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from assistant.assistant import Assistant  # noqa: E402
from assistant.text import normalize  # noqa: E402


def check(case: dict, r: dict) -> dict:
    reply = normalize(r["reply"])
    src = case["expected_source"]
    return {
        "intencja": r["intent"] == case["expected_intent"],
        "trasa": r["route"] == case["expected_route"],
        "zrodlo": True if not src else any(s == src or s.startswith(src + "#") for s in r["sources"]),
        "fakty": all(normalize(x) in reply for x in case["must_include"]),
        "zakazane": not any(normalize(x) in reply for x in case["must_not_include"]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["claude", "offline"])
    ap.add_argument("--cases", default="cases", help="cases (zestaw roboczy) albo cases_holdout (zestaw kontrolny)")
    args = ap.parse_args()

    bot = Assistant(mode=args.mode, log=False)
    cases = json.load(open(ROOT / "eval" / f"{args.cases}.json", encoding="utf-8"))
    rows, metrics = [], {k: 0 for k in ("intencja", "trasa", "zrodlo", "fakty", "zakazane")}
    unsafe_auto, tokens_in, tokens_out, latency = 0, 0, 0, []

    for c in cases:
        r = bot.handle(c["message"], c["email"])
        ok = check(c, r)
        for k, v in ok.items():
            metrics[k] += v
        if c["expected_route"] != "AUTO" and r["route"] == "AUTO":
            unsafe_auto += 1
        tokens_in += r["tokens"]["input_tokens"]; tokens_out += r["tokens"]["output_tokens"]
        latency.append(r["latency_ms"])
        rows.append({"id": c["id"], "wiadomosc": c["message"], "oczekiwana_intencja": c["expected_intent"], "wynik_intencja": r["intent"],
                     "oczekiwana_trasa": c["expected_route"], "wynik_trasa": r["route"], "zrodla": " ".join(r["sources"]),
                     **{f"ok_{k}": "✓" if v else "✗" for k, v in ok.items()}, "odpowiedz": r["reply"].replace("\n", " ")})
        status = "OK " if all(ok.values()) else "ERR"
        print(f"{status} {c['id']}  {r['intent']:<18} {r['route']:<10} {c['message'][:60]}")

    n = len(cases)
    stamp = datetime.now().strftime("%Y-%m-%d")
    mode = bot.mode + ("" if args.cases == "cases" else "_holdout")
    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(exist_ok=True)
    with open(out_dir / f"eval_{mode}_{stamp}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter=";")
        w.writeheader(); w.writerows(rows)

    labels = {"intencja": "Trafność intencji", "trasa": "Trafność trasy (AUTO/DRAFT/ESKALACJA)",
              "zrodlo": "Właściwe źródło w top 3", "fakty": "Odpowiedź zawiera wymagane fakty", "zakazane": "Brak treści zakazanych"}
    md = [f"# Wyniki ewaluacji: {bot.llm.name}", "", f"Data: {stamp} · zestaw: `{args.cases}.json` · przypadków: {n}", "",
          "| Metryka | Wynik |", "|---|---|"]
    md += [f"| {labels[k]} | {v}/{n} ({v / n:.0%}) |" for k, v in metrics.items()]
    md += [f"| **Niebezpieczne AUTO** (sprawa dla człowieka wysłana automatycznie) | **{unsafe_auto}** |",
           f"| Średni czas odpowiedzi | {sum(latency) / n:.0f} ms |"]
    if tokens_in:
        md.append(f"| Tokeny na wiadomość (wejście / wyjście) | {tokens_in // n} / {tokens_out // n} |")
    fails = [r for r in rows if "✗" in (r[f"ok_{k}"] for k in labels)]
    if fails:
        md += ["", "## Przypadki z błędami", "", "| ID | Wiadomość | Oczekiwano | Wynik | Nieudane sprawdzenia |", "|---|---|---|---|---|"]
        for r in fails:
            bad = ", ".join(k for k in labels if r[f"ok_{k}"] == "✗")
            md.append(f"| {r['id']} | {r['wiadomosc']} | {r['oczekiwana_intencja']} / {r['oczekiwana_trasa']} | {r['wynik_intencja']} / {r['wynik_trasa']} | {bad} |")
    (out_dir / f"eval_{mode}_{stamp}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n" + "\n".join(md[4:]))


if __name__ == "__main__":
    main()
