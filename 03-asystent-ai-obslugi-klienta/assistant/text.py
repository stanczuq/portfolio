"""Narzędzia tekstowe dla języka polskiego: normalizacja, tokeny, ekstrakcja danych, maskowanie PII."""
import re
import unicodedata

_PL = str.maketrans("łŁ", "lL")

STOPWORDS = {
    "a", "aby", "ale", "bo", "by", "byc", "czy", "do", "dla", "i", "ich", "ile", "jak", "jaki", "jest",
    "juz", "ja", "mi", "mam", "moje", "moj", "moja", "na", "nie", "o", "od", "po", "pod", "przez", "sie",
    "sa", "ta", "tak", "te", "to", "tu", "w", "we", "z", "za", "ze", "co", "u", "mnie", "czesc",
    "dzien", "dobry", "witam", "pozdrawiam", "prosze", "dziekuje", "bardzo", "moge", "mozna", "jesli",
}


def normalize(text: str) -> str:
    """Małe litery, bez polskich znaków, liczba + jednostka sklejone („500 g” -> „500g”)."""
    text = (text or "").translate(_PL).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"(\d)\s+(g|kg|ml|l|szt|kaps)\b", r"\1\2", text)


def stem(token: str) -> str:
    """Prosty stemming przez prefiks: „kreatyny” i „kreatyna” -> „kreat”.

    Wystarcza dla odmiany polskich rzeczowników w krótkiej bazie wiedzy.
    Przy większej bazie lepsze są embeddingi (patrz README, „Możliwe rozszerzenia”).
    """
    return token if token.isdigit() or len(token) <= 5 else token[:5]


def tokens(text: str) -> list[str]:
    return [stem(t) for t in re.findall(r"[a-z0-9]+", normalize(text)) if t not in STOPWORDS]


EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+48[\s-]?)?\b\d{3}[\s-]?\d{3}[\s-]?\d{3}\b")


def extract_order_number(text: str) -> str | None:
    t = normalize(text)
    m = re.search(r"#\s?(\d{4,6})\b", t) or re.search(r"\b(?:nr|numer|zamowien\w*)\D{0,15}?(\d{4,6})\b", t)
    return m.group(1) if m else None


def extract_email(text: str) -> str | None:
    m = EMAIL_RE.search(text or "")
    return m.group(0).lower() if m else None


def mask_pii(text: str) -> str:
    """Maskuje e-maile i telefony przed zapisaniem do logów (RODO: minimalizacja danych)."""
    text = EMAIL_RE.sub(lambda m: m.group(0)[0] + "***@" + m.group(0).split("@")[1], text or "")
    return PHONE_RE.sub("*** *** ***", text)
