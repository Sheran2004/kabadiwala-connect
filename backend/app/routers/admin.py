import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Lot, Sale
from ..schemas import BidIn
from ..security import require
from .market import notify, add_report
router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/overview")
def overview(u: User = Depends(require("admin")), db: Session = Depends(get_db)):
    cnt = lambda q: db.scalar(q) or 0
    return {"collectors": cnt(select(func.count(User.id)).where(User.role == "collector")),
            "recyclers": cnt(select(func.count(User.id)).where(User.role == "recycler")),
            "pending": cnt(select(func.count(User.id)).where(User.role == "recycler", User.verified == False)),  # noqa: E712
            "open_lots": cnt(select(func.count(Lot.id)).where(Lot.status == "open")), "sales": cnt(select(func.count(Sale.id))),
            "volume": cnt(select(func.sum(Sale.amount)))}

@router.get("/recyclers")
def recyclers(u: User = Depends(require("admin")), db: Session = Depends(get_db)):
    rows = db.scalars(select(User).where(User.role == "recycler").order_by(User.verified, User.created.desc())).all()
    return [{"id": r.id, "name": r.name, "phone": r.phone, "verified": bool(r.verified), "created": r.created} for r in rows]

def _set(uid, v, db):
    r = db.get(User, uid)
    if not r or r.role != "recycler": raise HTTPException(404, "Recycler not found")
    r.verified, r.verified_at = v, time.time() if v else None
    if v: notify(db, uid, "approved", who="Admin")
    db.commit(); return {"ok": True}

@router.post("/recyclers/{uid}/approve")
def approve(uid: str, u: User = Depends(require("admin")), db: Session = Depends(get_db)): return _set(uid, True, db)

@router.post("/recyclers/{uid}/revoke")
def revoke(uid: str, u: User = Depends(require("admin")), db: Session = Depends(get_db)): return _set(uid, False, db)

@router.put("/rates/{t}")
def set_rate(t: str, b: BidIn, u: User = Depends(require("admin")), db: Session = Depends(get_db)):
    add_report(db, t, b.amount, u.id); return {"ok": True}
