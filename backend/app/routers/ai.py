"""AI endpoints. Keys live ONLY on the server (backend/.env) - never in the frontend.
If the configured model has been retired (HTTP 404/400) the app auto-discovers a working model for your key."""
import json, re, time, urllib.request, urllib.error
from collections import defaultdict, deque
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .. import config as C
from ..database import get_db
from ..models import User, Rate
from ..security import current_user
router = APIRouter(prefix="/ai", tags=["ai"])
_hits = defaultdict(deque); _auto = {}
UA = {"User-Agent": "KabadiwalaConnect/1.0"}
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"

@router.get("/status")
def status():
    return {"groq": bool(C.GROQ_API_KEY), "gemini": bool(C.GEMINI_API_KEY), "groq_model": _auto.get("groq", C.GROQ_MODEL), "gemini_model": _auto.get("gemini", C.GEMINI_MODEL)}

def limit(uid, n=20):
    q, now = _hits[uid], time.time()
    while q and now - q[0] > 60: q.popleft()
    if len(q) >= n: raise HTTPException(429, "Too many AI requests. Please wait a minute.")
    q.append(now)

def _open(req):
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())

def post(url, body, headers):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **UA, **headers})
    try: return _open(req)
    except urllib.error.HTTPError as e:
        try: why = json.loads(e.read()).get("error", {}); why = why.get("message", "") if isinstance(why, dict) else str(why)
        except Exception: why = ""
        ex = HTTPException(502, f"AI provider error {e.code}: {why[:160]}"); ex.provider_code = e.code; raise ex
    except Exception: raise HTTPException(502, "AI provider unreachable")

def get(url, headers):
    try: return _open(urllib.request.Request(url, headers={**UA, **headers}))
    except Exception: raise HTTPException(502, "Could not list the AI models for this key")

def pick_groq():
    ids = [m["id"] for m in get("https://api.groq.com/openai/v1/models", {"Authorization": "Bearer " + C.GROQ_API_KEY}).get("data", []) if m.get("active", True)]
    ids = [i for i in ids if not any(b in i for b in ("whisper", "guard", "tts", "orpheus", "embed", "safeguard"))]
    _auto["groq_list"] = ids
    for pref in ("gpt-oss-120b", "llama-3.3-70b", "llama-4", "gpt-oss-20b", "qwen", "llama-3.1-8b"):
        for i in ids:
            if pref in i: return i
    if ids: return ids[0]
    raise HTTPException(502, "No usable Groq model for this key")

def pick_gemini():
    ok = []
    for m in get(GEMINI_URL + "?pageSize=200", {"x-goog-api-key": C.GEMINI_API_KEY}).get("models", []):
        n = m["name"].split("/")[-1]
        if "generateContent" in m.get("supportedGenerationMethods", []) and "flash" in n and not any(b in n for b in ("lite", "image", "tts", "live", "audio", "thinking", "exp", "embed", "robotics", "computer")):
            v = re.search(r"gemini-(\d+(?:\.\d+)?)", n); ok.append((float(v.group(1)) if v else 0, n))
    _auto["gemini_list"] = [n for _, n in sorted(ok, reverse=True)]
    if not ok: raise HTTPException(502, "No usable Gemini model for this key")
    return max(ok, key=lambda x: (x[0], -len(x[1])))[1]

def groq(messages):
    def go(m):  # gpt-oss models "think" first: keep reasoning low and leave room for the answer
        body = {"model": m, "temperature": 0.4, "max_tokens": 900, "messages": messages}
        if "gpt-oss" in m: body["reasoning_effort"] = "low"
        return post("https://api.groq.com/openai/v1/chat/completions", body, {"Authorization": "Bearer " + C.GROQ_API_KEY})
    try: d = go(_auto.get("groq", C.GROQ_MODEL))
    except HTTPException as e:
        if getattr(e, "provider_code", None) not in (400, 404): raise
        _auto["groq"] = pick_groq(); d = go(_auto["groq"])
    text = (d["choices"][0]["message"].get("content") or "").strip()
    if not text: raise HTTPException(502, "Empty AI reply")
    return text

def gemini(body):
    def go(m): return post(f"{GEMINI_URL}/{m}:generateContent", body, {"x-goog-api-key": C.GEMINI_API_KEY})
    try: d = go(_auto.get("gemini", C.GEMINI_MODEL))
    except HTTPException as e:
        if getattr(e, "provider_code", None) not in (400, 404): raise
        _auto["gemini"] = pick_gemini(); d = go(_auto["gemini"])
    return d["candidates"][0]["content"]["parts"][0]["text"].strip()

SYS = ("You are Kabadiwala Mitra, the assistant inside Kabadiwala Connect, an app where scrap collectors (kabadiwalas) sell scrap "
       "to recyclers and keep a digital income record. Help with: scrap rates, how to sell and take bids in the app, "
       "getting better prices (sorting, keeping metals and e-waste separate), safe handling, and income records for loans. "
       "Answer in at most 4 short sentences with simple words. Never invent prices: use only the rates given. "
       "If asked about something unrelated, say briefly that you only help with scrap selling. ")

class Msg(BaseModel):
    role: Literal["user", "assistant"]; content: str = Field(max_length=1000)
class ChatIn(BaseModel):
    messages: list[Msg] = Field(min_length=1, max_length=12); lang: Literal["en", "hi"] = "en"

@router.post("/chat")
def chat(b: ChatIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    limit(u.id)
    rates = ", ".join(f"{r.type} Rs{r.price:g}/kg" for r in db.scalars(select(Rate)))
    sysmsg = SYS + f"Current platform rates: {rates}. " + ("Reply in simple Hindi (Devanagari script)." if b.lang == "hi" else "Reply in simple English; if the user writes Hinglish, reply in Hinglish.")
    try:
        if C.GROQ_API_KEY:
            try: return {"reply": groq([{"role": "system", "content": sysmsg}, *[m.model_dump() for m in b.messages]]), "provider": "groq"}
            except HTTPException:
                if not C.GEMINI_API_KEY: raise
        if C.GEMINI_API_KEY:
            return {"reply": gemini({"system_instruction": {"parts": [{"text": sysmsg}]},
                    "contents": [{"role": "user" if m.role == "user" else "model", "parts": [{"text": m.content}]} for m in b.messages]}), "provider": "gemini"}
    except (KeyError, IndexError): raise HTTPException(502, "Unexpected AI response")
    raise HTTPException(503, "AI is not configured. Add GROQ_API_KEY (or GEMINI_API_KEY) to backend/.env and restart.")

class ScanIn(BaseModel):
    image: str = Field(max_length=3_000_000); mime: Literal["image/jpeg", "image/png", "image/webp"] = "image/jpeg"

@router.post("/scan")
def scan(b: ScanIn, u: User = Depends(current_user)):
    limit(u.id, 10)
    if not C.GEMINI_API_KEY: raise HTTPException(503, "Photo scan needs GEMINI_API_KEY in backend/.env")
    from ..config import RATES
    prompt = (f"You are a scrap sorter. Look at the photo and pick the main scrap material. type must be one of {list(RATES)} "
              "(paper=newspaper/paper, card=cardboard, pet=plastic, iron, alu=aluminium, brass, cu=copper, glass, ew=e-waste). "
              'Estimate total weight in kg (0 if you cannot tell). Reply ONLY JSON: {"type":"...","kg":number,"note":"one short sentence"}')
    try:
        text = gemini({"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": b.mime, "data": b.image}}]}], "generationConfig": {"responseMimeType": "application/json"}})
        r = json.loads(text.strip().strip("`").removeprefix("json").strip()); t = r.get("type"); kg = float(r.get("kg") or 0)
    except HTTPException: raise
    except Exception: raise HTTPException(502, "Could not read the photo. Try a clearer picture.")
    return {"type": t if t in RATES else None, "kg": round(max(0, min(kg, 5000)), 1), "note": str(r.get("note", ""))[:200]}
