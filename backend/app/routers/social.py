import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Lot, Bid, Sale, Rating, Message
from ..schemas import RateIn, MsgIn
from ..security import current_user
from .market import notify, rating_of
router = APIRouter(tags=["social"])

@router.post("/sales/{sid}/rate")
def rate_sale(sid: str, b: RateIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    s = db.get(Sale, sid)
    if not s or u.id not in (s.seller_id, s.buyer_id): raise HTTPException(404, "Sale not found")
    if (s.stage or "scheduled") != "picked_up": raise HTTPException(409, "You can rate after the pickup is done")
    if db.scalar(select(Rating.id).where(Rating.sale_id == sid, Rating.from_id == u.id)): raise HTTPException(409, "You already rated this sale")
    to = s.buyer_id if u.id == s.seller_id else s.seller_id
    db.add(Rating(sale_id=sid, from_id=u.id, to_id=to, stars=b.stars, comment=b.comment)); notify(db, to, "rate", who=u.name, stars=b.stars, lot=s.lot_id)
    db.commit(); return {"ok": True}

@router.get("/users/{uid}/rating")
def user_rating(uid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Rating.stars, Rating.comment).where(Rating.to_id == uid, Rating.comment != "").order_by(Rating.created.desc()).limit(5)).all()
    return {**rating_of(db, uid), "recent": [{"stars": s, "comment": c} for s, c in rows]}

def can_chat(db, u, lot, peer):
    l = db.get(Lot, lot)
    if not l: return False
    if u.id == l.owner_id: other = peer
    elif peer == l.owner_id: other = u.id
    else: return False
    return bool(db.scalar(select(Bid.id).where(Bid.lot_id == lot, Bid.buyer_id == other)))

@router.get("/lots/{lot}/messages")
def get_msgs(lot: str, peer: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    if not can_chat(db, u, lot, peer): raise HTTPException(403, "Chat is only between the lot owner and recyclers who bid on it")
    rows = db.scalars(select(Message).where(Message.lot_id == lot, or_(and_(Message.sender_id == u.id, Message.receiver_id == peer), and_(Message.sender_id == peer, Message.receiver_id == u.id))).order_by(Message.created).limit(200)).all()
    for m in rows:
        if m.receiver_id == u.id and not m.read: m.read = True
    db.commit(); return [{"id": m.id, "mine": m.sender_id == u.id, "text": m.text, "created": m.created} for m in rows]

@router.post("/lots/{lot}/messages")
def send_msg(lot: str, b: MsgIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    if not can_chat(db, u, lot, b.peer): raise HTTPException(403, "Chat is only between the lot owner and recyclers who bid on it")
    if db.scalar(select(func.count(Message.id)).where(Message.sender_id == u.id, Message.created > time.time() - 60)) >= 20: raise HTTPException(429, "Slow down: too many messages")
    db.add(Message(lot_id=lot, sender_id=u.id, receiver_id=b.peer, text=b.text.strip())); notify(db, b.peer, "msg", who=u.name, lot=lot, text=b.text.strip()[:60], peer=u.id)
    db.commit(); return {"ok": True}
