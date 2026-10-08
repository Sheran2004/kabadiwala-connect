"""After a bid is accepted: pickup tracking (buyer) and payment confirmation (buyer says sent, seller confirms received)."""
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Sale
from ..schemas import StageIn, PayIn
from ..security import require
from .market import notify
router = APIRouter(prefix="/sales", tags=["orders"])
ORDER = {"scheduled": 0, "on_the_way": 1, "picked_up": 2}

def _sale(db, sid, u, side):
    s = db.get(Sale, sid)
    if not s or (s.buyer_id if side == "buyer" else s.seller_id) != u.id: raise HTTPException(404, "Order not found")
    return s

@router.post("/{sid}/stage")
def set_stage(sid: str, b: StageIn, u: User = Depends(require("recycler")), db: Session = Depends(get_db)):
    s = _sale(db, sid, u, "buyer")
    if ORDER[b.stage] != ORDER[s.stage or "scheduled"] + 1: raise HTTPException(409, "Do the steps in order: On the way, then Picked up")
    s.stage, s.stage_at = b.stage, time.time()
    notify(db, s.seller_id, "ontheway" if b.stage == "on_the_way" else "pickedup", who=u.name, lot=s.lot_id)
    db.commit(); return {"ok": True}

@router.post("/{sid}/pay")
def pay_sent(sid: str, b: PayIn, u: User = Depends(require("recycler")), db: Session = Depends(get_db)):
    s = _sale(db, sid, u, "buyer")
    if (s.stage or "scheduled") != "picked_up": raise HTTPException(409, "Mark the pickup as done first")
    if s.pay_status == "confirmed": raise HTTPException(409, "Payment is already confirmed")
    s.pay_status, s.pay_method, s.pay_ref, s.pay_at = "sent", b.method, ((b.ref or "").strip()[:40] or None), time.time()
    notify(db, s.seller_id, "paysent", who=u.name, lot=s.lot_id, amount=s.amount)
    db.commit(); return {"ok": True}

@router.post("/{sid}/confirm")
def confirm_received(sid: str, u: User = Depends(require("collector")), db: Session = Depends(get_db)):
    s = _sale(db, sid, u, "seller")
    if (s.stage or "scheduled") != "picked_up": raise HTTPException(409, "The buyer has not picked up yet")
    if s.pay_status == "confirmed": raise HTTPException(409, "Payment is already confirmed")
    s.pay_status, s.pay_at = "confirmed", time.time(); s.pay_method = s.pay_method or "cash"
    notify(db, s.buyer_id, "payok", who=u.name, lot=s.lot_id, amount=s.amount)
    db.commit(); return {"ok": True}
