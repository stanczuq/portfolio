"""Przepisuje wyniki najnowszej ewaluacji Claude (zestaw kontrolny) do tabeli w README.md.

    python eval/update_readme.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "eval" / "results"
ROWS = {  # wiersz w README -> początek wiersza w raporcie ewaluacji
    "Trafność intencji": "Trafność intencji",
    "Trafność trasy": "Trafność trasy",
    "Właściwe źródło w top 3": "Właściwe źródło w top 3",
    "Odpowiedź zawiera wymagane fakty": "Odpowiedź zawiera wymagane fakty",
    "Brak treści zakazanych": "Brak treści zakazanych",
    "**Niebezpieczne AUTO**": "**Niebezpieczne AUTO**",
}


def latest(pattern: str) -> Path | None:
    files = sorted(RES.glob(pattern))
    return files[-1] if files else None


def metrics(md: Path) -> dict:
    out = {}
    for line in md.read_text(encoding="utf-8").splitlines():
        for key, start in ROWS.items():
            if line.startswith(f"| {start}"):
                val = line.rstrip(" |").split("|")[-1].strip()
                m = re.search(r"\((\d+%)\)", val)
                out[key] = m.group(1) if m else val
    return out


def main() -> None:
    md = latest("eval_claude_holdout_*.md")
    if not md:
        print("Brak wyników eval_claude_holdout_*.md. Najpierw: python eval/run_eval.py --mode claude --cases cases_holdout")
        return
    vals = metrics(md)
    readme = ROOT / "README.md"
    lines = readme.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        for key, v in vals.items():
            if line.startswith(f"| {key}") and "_uzupełnij_" in line:
                cells = line.split("|")
                cells[-2] = f" {('**' + v + '**') if key.startswith('**') else v} "
                lines[i] = "|".join(cells)
    readme.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"README zaktualizowane wynikami z {md.name}: {vals}")


if __name__ == "__main__":
    main()
