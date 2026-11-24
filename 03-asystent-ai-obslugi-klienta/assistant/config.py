import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = ROOT / "knowledge"
DATA_DIR = ROOT / "data"
LOG_FILE = ROOT / "logs" / "zgloszenia.jsonl"

# Tryb: "claude" (wymaga ANTHROPIC_API_KEY) albo "offline". Domyślnie: claude, jeśli jest klucz.
MODE = os.getenv("ASSISTANT_MODE") or ("claude" if os.getenv("ANTHROPIC_API_KEY") else "offline")
MODEL = os.getenv("ASSISTANT_MODEL", "claude-haiku-5-5")
API_KEY = os.getenv("ASSISTANT_API_KEY", "")   # klucz do własnego API (nagłówek X-API-Key), pusty = bez autoryzacji
