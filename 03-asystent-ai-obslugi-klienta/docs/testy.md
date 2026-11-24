# Testy i lista kontrolna przed publikacją

## 1. Testy jednostkowe
`python -m pytest -q`: 13 testów (weryfikacja właściciela zamówienia, pytania zdrowotne, prompt injection, groźby prawne,
zamówienie wstrzymane, strażnik wyjścia, maskowanie PII, ekstrakcja numerów, ścieżka Claude z podmienionym API).

## 2. Ewaluacja z modelem Claude (do zrobienia z kluczem API)
1. `.env` z `ANTHROPIC_API_KEY`.
2. `python eval/run_eval.py --mode claude` i `python eval/run_eval.py --mode claude --cases cases_holdout`.
3. Wyniki z `eval/results/eval_claude*.md` przepisz do tabeli w README i do `opis-do-cv.md`.
4. Przejrzyj kolumnę `odpowiedz` w CSV: czy ton i długość pasują do sklepu? Popraw `REPLY_SYSTEM` w `assistant/prompts.py` i uruchom ponownie.
5. **Nie poprawiaj niczego pod zestaw kontrolny.** Jeśli coś poprawisz, dopisz nowe przypadki kontrolne i opisz to w README.

## 3. Scenariusz Make
Przypadki M1–M5 w [`make/scenariusz-obsluga-maili.md`](../make/scenariusz-obsluga-maili.md).

## Zrzuty ekranu w `docs/screenshots/`

| Plik | Stan |
|---|---|
| `01-status-zamowienia.png` … `05-prompt-injection.png` | gotowe (widget, tryb offline) |
| `06-widget-claude.png` | do zrobienia: ta sama rozmowa w trybie Claude (widać tokeny) |
| `07-make-scenariusz.png` | do zrobienia: scenariusz w Make, wszystkie 3 trasy |
| `08-gmail-szkic.png` | do zrobienia: szkic odpowiedzi w Gmailu z etykietą `AI/Do akceptacji` |
| `09-slack-eskalacja.png` | do zrobienia: alert na `#obsluga-pilne` |

Na zrzutach zasłoń adres API, klucze i prawdziwe e-maile.

## Przed `git push`
- `.env` nie jest w repozytorium (jest w `.gitignore`), w `logs/` nie ma plików `.jsonl`.
- W eksporcie blueprintu z Make usuń adres API i klucz (szukaj `X-API-Key` i `https://`).
