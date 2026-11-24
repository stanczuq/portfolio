"""Rozmowa z asystentem w terminalu.

    python cli.py                                   # tryb interaktywny
    python cli.py -m "Ile kosztuje dostawa?"        # jedno pytanie
    python cli.py --email tomasz.wojcik@example.com # jako zalogowany klient
"""
import argparse

from assistant.assistant import Assistant

COLORS = {"AUTO": "\033[32m", "DRAFT": "\033[33m", "ESKALACJA": "\033[31m"}


def show(r: dict) -> None:
    print(f"\n{r['reply']}\n")
    print(f"{COLORS[r['route']]}[{r['route']}]\033[0m {r['intent']} · {r['sentiment']} · pewność {r['confidence']:.0%} · {r['latency_ms']} ms")
    print(f"  powód: {'; '.join(r['reasons'])}")
    print(f"  źródła: {', '.join(r['sources']) or '-'}\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--message")
    ap.add_argument("--email")
    ap.add_argument("--mode", choices=["claude", "offline"])
    args = ap.parse_args()
    bot = Assistant(mode=args.mode)
    print(f"Silnik: {bot.llm.name}")
    if args.message:
        return show(bot.handle(args.message, args.email, channel="cli"))
    history = []
    while True:
        try:
            msg = input("Ty> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if msg in ("", "exit", "koniec"):
            break
        r = bot.handle(msg, args.email, history, channel="cli")
        history += [{"role": "user", "content": msg}, {"role": "assistant", "content": r["reply"]}]
        show(r)


if __name__ == "__main__":
    main()
