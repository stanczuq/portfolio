"""API asystenta: czat na stronie sklepu i obsługa maili przez Make.

    uvicorn api.server:app --reload --port 8000
    http://localhost:8000          widget czatu z panelem „pod maską”
    http://localhost:8000/docs     dokumentacja API (Swagger)
"""
import sys
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from assistant import config  # noqa: E402
from assistant.assistant import Assistant  # noqa: E402

app = FastAPI(title="VitaForge · Asystent AI obsługi klienta", version="1.0")
bot = Assistant()


def require_key(x_api_key: str = Header(default="")) -> None:
    """Endpoint /email jest wywoływany z Make przez internet, więc wymaga klucza (nagłówek X-API-Key)."""
    if config.API_KEY and x_api_key != config.API_KEY:
        raise HTTPException(status_code=401, detail="Nieprawidłowy klucz API")


class Msg(BaseModel):
    role: str
    content: str


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    email: str | None = Field(None, description="E-mail zalogowanego klienta (weryfikacja przy pytaniach o zamówienie)")
    history: list[Msg] = []


class EmailIn(BaseModel):
    from_email: str = Field(..., alias="from")
    subject: str = ""
    body: str
    thread_id: str | None = None


@app.get("/")
def widget():
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "engine": bot.llm.name, "kb_chunks": len(bot.kb.chunks)}


@app.post("/chat")
def chat(inp: ChatIn):
    return bot.handle(inp.message, inp.email, [m.model_dump() for m in inp.history], channel="chat")


@app.post("/email", dependencies=[Depends(require_key)])
def email(inp: EmailIn):
    """Wejście dla scenariusza Make (Gmail › Watch emails -> HTTP -> ten endpoint).

    Zwraca wszystko, czego router w Make potrzebuje: trasę, gotowy temat i treść odpowiedzi,
    etykietę do Gmaila i krótkie podsumowanie na Slacka.
    """
    text = f"{inp.subject}\n{inp.body}".strip()
    r = bot.handle(text, inp.from_email, channel="email")
    subject = inp.subject if inp.subject.lower().startswith("re:") else f"Re: {inp.subject or 'Twoja wiadomość'}"
    return {
        **r,
        "thread_id": inp.thread_id,
        "reply_subject": subject,
        "gmail_label": {"AUTO": "AI/Wysłane", "DRAFT": "AI/Do akceptacji", "ESKALACJA": "AI/Pilne"}[r["route"]],
        "slack_text": (f"*{r['route']}* · {r['intent']} · nastrój: {r['sentiment']}\n"
                       f"Od: {inp.from_email} · Temat: {inp.subject}\nPowód: {'; '.join(r['reasons'])}"),
    }
