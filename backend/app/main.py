import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from . import config as C
from .database import Base, engine, SessionLocal, migrate
from .models import Rate, User
from .routers import auth, market, insights, ai, social, admin, orders
from .security import new_salt, hash_pw

Base.metadata.create_all(engine); migrate()
WEAK_PW = {"admin12345", "password", "12345678", "admin@123", "password123"}
with SessionLocal() as _db:
    for _k, _v in C.RATES.items():
        _r = _db.get(Rate, _k)
        if not _r: _db.add(Rate(type=_k, price=_v))
        elif _r.by_id is None and _r.price != _v: _r.price = _v   # refresh starting rates until someone reports a real price
    _ap, _pw = os.getenv("ADMIN_PHONE", "").strip(), os.getenv("ADMIN_PASSWORD", "")   # creates the first admin on a fresh server
    if _ap and _pw and not _db.scalar(select(User).where(User.phone == _ap)):
        if C.PROD and (len(_pw) < 10 or _pw.lower() in WEAK_PW): print("[SECURITY] ADMIN_PASSWORD is too weak (min 10 chars, not a common password). Admin NOT created.", flush=True)
        else:
            _s = new_salt(); _db.add(User(phone=_ap, name=os.getenv("ADMIN_NAME", "Admin"), role="admin", salt=_s, pw_hash=hash_pw(_pw, _s), verified=True))
    _db.commit()
if C.PROD:
    if C.DEBUG_OTP: print("[SECURITY WARNING] KC_DEBUG_OTP=1 -> OTPs are returned in API responses. Demo only!", flush=True)
    if C.ORIGINS == ["*"]: print("[SECURITY WARNING] KC_ORIGINS is '*'. Set it to your frontend URL.", flush=True)

app = FastAPI(title="Kabadiwala Connect API", version="2.1.0", docs_url=None if C.PROD else "/docs", redoc_url=None, openapi_url=None if C.PROD else "/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=C.ORIGINS, allow_methods=["*"], allow_headers=["*"])
@app.middleware("http")
async def security_headers(request, call_next):
    r = await call_next(request)
    r.headers.setdefault("X-Content-Type-Options", "nosniff"); r.headers.setdefault("X-Frame-Options", "DENY"); r.headers.setdefault("Referrer-Policy", "no-referrer")
    return r
for r in (auth, market, insights, ai, social, admin, orders): app.include_router(r.router)
@app.get("/health")
def health(): return {"ok": True}
