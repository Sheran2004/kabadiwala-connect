import hashlib, secrets, time
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .. import config as C
from ..database import get_db
from ..models import User, Otp
from ..ratelimit import by_phone, by_ip, client_ip
from ..schemas import Reg, Login, LoginOtp, OtpReq, ChangePw, ResetPw
from ..security import new_salt, hash_pw, make_token, current_user
from .. import sms
router = APIRouter(prefix="/auth", tags=["auth"])
out = lambda u: {"token": make_token(u.id), "role": u.role, "name": u.name, "verified": bool(u.verified)}
hcode = lambda code: hashlib.sha256((code + C.SECRET).encode()).hexdigest()

def check_otp(db: Session, phone: str, code: str):
    o = db.scalar(select(Otp).where(Otp.phone == phone).order_by(Otp.created.desc()))
    if not o or o.expires < time.time() or o.attempts >= 5: raise HTTPException(400, "OTP expired or used up. Request a new one.")
    o.attempts += 1
    try: ok = sms.verify_managed(phone, code) if o.code_hash == "managed" else secrets.compare_digest(o.code_hash, hcode(code))
    except Exception as e:
        print(f"[SMS ERROR] verify: {type(e).__name__}: {e}", flush=True); db.commit(); raise HTTPException(502, "Could not verify the OTP right now. Try again.")
    if ok: o.expires = 0   # single use
    db.commit()
    if not ok: raise HTTPException(400, "Wrong OTP")

@router.post("/otp/request")
def otp_request(b: OtpReq, db: Session = Depends(get_db)):
    now = time.time(); last = db.scalar(select(Otp).where(Otp.phone == b.phone).order_by(Otp.created.desc()))
    if last and now - last.created < 30: raise HTTPException(429, "Please wait 30 seconds before asking for another OTP.")
    if db.scalar(select(func.count(Otp.id)).where(Otp.phone == b.phone, Otp.created > now - 3600)) >= 5: raise HTTPException(429, "Too many OTP requests. Try again in an hour.")
    managed = sms.is_managed()   # Fast2SMS OTP API: the provider creates and checks the code
    code = None if managed else f"{secrets.randbelow(10**6):06d}"
    try: sms.send_managed(b.phone) if managed else sms.send_otp(b.phone, code)
    except Exception as e:
        print(f"[SMS ERROR] {type(e).__name__}: {e}", flush=True); raise HTTPException(502, "Could not send the SMS. Try again later.")
    db.add(Otp(phone=b.phone, code_hash="managed" if managed else hcode(code), expires=now + 300)); db.commit()
    return {"sent": True, "dev_code": code if (C.DEBUG_OTP and code) else None}

@router.post("/register")
def register(b: Reg, db: Session = Depends(get_db)):
    check_otp(db, b.phone, b.code)
    if db.scalar(select(User).where(User.phone == b.phone)): raise HTTPException(409, "Phone already registered")
    s = new_salt(); u = User(phone=b.phone, name=b.name, role=b.role, salt=s, pw_hash=hash_pw(b.password, s), verified=False)
    db.add(u); db.commit(); return out(u)

@router.post("/login")
def login(b: Login, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request); by_phone.check(b.phone); by_ip.check(ip)
    u = db.scalar(select(User).where(User.phone == b.phone))
    if not u or not secrets.compare_digest(u.pw_hash, hash_pw(b.password, u.salt)):
        by_phone.hit(b.phone); by_ip.hit(ip); raise HTTPException(401, "Wrong phone or password")
    by_phone.reset(b.phone); return out(u)

@router.post("/login-otp")
def login_otp(b: LoginOtp, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.phone == b.phone))
    if not u: raise HTTPException(404, "No account for this number. Register first.")
    check_otp(db, b.phone, b.code); return out(u)

@router.post("/change-password")
def change_password(b: ChangePw, u: User = Depends(current_user), db: Session = Depends(get_db)):
    key = "pw:" + u.id; by_phone.check(key)
    if not secrets.compare_digest(u.pw_hash, hash_pw(b.current, u.salt)): by_phone.hit(key); raise HTTPException(400, "Current password is wrong")
    if b.current == b.new: raise HTTPException(400, "Choose a different password")
    s = new_salt(); u.salt, u.pw_hash = s, hash_pw(b.new, s); db.commit(); by_phone.reset(key); return {"ok": True}

@router.post("/reset-password")
def reset_password(b: ResetPw, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.phone == b.phone))
    if not u: raise HTTPException(404, "No account for this number.")
    check_otp(db, b.phone, b.code)
    s = new_salt(); u.salt, u.pw_hash = s, hash_pw(b.new, s); db.commit(); by_phone.reset(b.phone); return out(u)

@router.get("/me")
def me(u: User = Depends(current_user)): return {"name": u.name, "role": u.role, "phone": u.phone, "verified": bool(u.verified)}
