import hashlib, secrets, time, jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .config import SECRET
from .database import get_db
from .models import User
bearer = HTTPBearer()
def new_salt(): return secrets.token_hex(8)
def hash_pw(pw, salt): return hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000).hex()
def make_token(uid): return jwt.encode({"sub": uid, "exp": int(time.time()) + 7 * 86400}, SECRET, "HS256")
def current_user(cr: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    try: uid = jwt.decode(cr.credentials, SECRET, ["HS256"])["sub"]
    except jwt.PyJWTError: raise HTTPException(401, "Invalid or expired token")
    u = db.get(User, uid)
    if not u: raise HTTPException(401, "Invalid or expired token")
    return u
def require(role):
    def dep(u: User = Depends(current_user)):
        if u.role != role: raise HTTPException(403, f"Only {role} can do this")
        return u
    return dep

def require_verified_recycler(u: User = Depends(require("recycler"))):
    if not u.verified: raise HTTPException(403, "Your recycler account is waiting for admin approval.")
    return u
