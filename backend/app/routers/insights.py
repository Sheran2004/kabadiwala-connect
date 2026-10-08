import json
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Lot, Sale, Notification
from ..security import current_user
router = APIRouter(tags=["insights"])

@router.get("/stats")
def stats(u: User = Depends(current_user), db: Session = Depends(get_db)):
    col = u.role == "collector"; c = Sale.seller_id if col else Sale.buyer_id
    rows = db.execute(select(Sale.type, func.sum(Sale.amount), func.sum(Sale.kg)).where(c == u.id).group_by(Sale.type)).all()
    amount = sum(r[1] or 0 for r in rows); kg = sum(r[2] or 0 for r in rows)
    q = select(func.count(Lot.id)).where(Lot.status == "open")
    if col: q = q.where(Lot.owner_id == u.id)
    return {"amount": amount, "kg": round(kg, 1), "open": db.scalar(q), "avg": round(amount / kg, 1) if kg else 0,
            "by_type": [{"type": t, "amount": a} for t, a, _ in sorted(rows, key=lambda r: -(r[1] or 0))]}

@router.get("/notifications")
def notes(u: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).where(Notification.user_id == u.id).order_by(Notification.created.desc()).limit(20)).all()
    return {"unread": sum(1 for r in rows if not r.read),
            "items": [{"id": r.id, "kind": r.kind, "data": json.loads(r.data), "read": r.read, "created": r.created} for r in rows]}

@router.post("/notifications/read")
def read_all(u: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(update(Notification).where(Notification.user_id == u.id, Notification.read == False).values(read=True)); db.commit()  # noqa: E712
    return {"ok": True}
