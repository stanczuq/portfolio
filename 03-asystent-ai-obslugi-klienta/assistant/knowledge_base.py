"""Baza wiedzy (RAG): pliki Markdown dzielone na sekcje i wyszukiwane algorytmem BM25.

Każda sekcja „## …” to osobny fragment z własnym identyfikatorem (np. `zwroty#termin-zwrotu`),
dzięki czemu odpowiedź zawsze wskazuje źródło, a ewaluacja sprawdza, czy znaleziono właściwy fragment.
"""
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .text import normalize, tokens


@dataclass
class Chunk:
    id: str
    doc: str
    title: str
    text: str


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalize(s)).strip("-")


class KnowledgeBase:
    def __init__(self, folder: Path, k1: float = 1.4, b: float = 0.75):
        self.chunks: list[Chunk] = []
        for path in sorted(Path(folder).glob("*.md")):
            doc = path.stem
            for block in re.split(r"^## ", path.read_text(encoding="utf-8"), flags=re.M)[1:]:
                title, _, body = block.partition("\n")
                self.chunks.append(Chunk(f"{doc}#{_slug(title)}", doc, title.strip(), body.strip()))

        # Tytuł sekcji liczony podwójnie: „Termin zwrotu” mówi o fragmencie więcej niż jedno słowo w treści.
        self._docs = [tokens(c.title) * 2 + tokens(c.text) for c in self.chunks]
        self._tf = [Counter(d) for d in self._docs]
        self._avgdl = sum(map(len, self._docs)) / max(len(self._docs), 1)
        df = Counter(t for d in self._docs for t in set(d))
        n = len(self._docs)
        self._idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.k1, self.b = k1, b

    def search(self, query: str, k: int = 3, min_score: float = 1.0,
               prefer_docs: list[str] | None = None, boost: float = 1.6) -> list[tuple[Chunk, float]]:
        """BM25 z opcjonalnym wzmocnieniem dokumentów pasujących do intencji
        (pytanie o pęknięte opakowanie białka ma trafić do reklamacji, a nie do opisu białka)."""
        q = set(tokens(query))
        scored = []
        for chunk, tf, doc in zip(self.chunks, self._tf, self._docs):
            s = 0.0
            for t in q:
                if t in tf:
                    f = tf[t]
                    s += self._idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(doc) / self._avgdl))
            if prefer_docs and chunk.doc in prefer_docs:
                s *= boost
            if s >= min_score:
                scored.append((chunk, round(s, 2)))
        return sorted(scored, key=lambda x: -x[1])[:k]

    def get(self, chunk_id: str) -> Chunk | None:
        return next((c for c in self.chunks if c.id == chunk_id), None)
