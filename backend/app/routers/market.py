import uuid, json, time, datetime, statistics
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from ..config import RATES, REF, REF_DATE
from ..database import get_db
from ..models import User, Lot, Bid, Sale, Rate, RateReport, Notification, Rating
from ..schemas import LotIn, LotEdit, BidIn
from ..security import current_user, require, require_verified_recycler
router = APIRouter(tags=["market"])

def lot_d(l, **x):
    return {"id": l.id, "type": l.type, "kg": l.kg, "city": l.city, "status": l.status, "created": l.created, "lat": l.lat, "lng": l.lng,
            "address": l.address, "pickup_date": l.pickup_date, "pickup_slot": l.pickup_slot, **x}

def notify(db, uid, kind, **data):
    db.add(Notification(user_id=uid, kind=kind, data=json.dumps(data)[:300]))

def rating_of(db, uid):
    a, n = db.execute(select(func.avg(Rating.stars), func.count(Rating.id)).where(Rating.to_id == uid)).one()
    return {"avg": round(a, 1) if a else None, "n": n}

def check_pickup(d):
    if not d: return
    try: x = datetime.date.fromisoformat(d)
    except ValueError: raise HTTPException(422, "Invalid pickup date")
    today = datetime.date.today()
    if x < today or x > today + datetime.timedelta(days=60): raise HTTPException(422, "Pickup date must be within the next 60 days")

def price_of(db, t):
    r = db.get(Rate, t); return r.price if r else RATES[t]

def add_report(db, t, price, uid):
    """Stores a price report; the shown rate is the MEDIAN of reports from the last 7 days (one wild report cannot move it much)."""
    if t not in RATES or price > RATES[t] * 4 or price < RATES[t] / 4: raise HTTPException(422, "That price looks wrong for this scrap type")
    db.add(RateReport(type=t, price=price, by_id=uid)); db.flush()
    ps = [p for (p,) in db.execute(select(RateReport.price).where(RateReport.type == t, RateReport.created > time.time() - 7 * 86400))]
    med = round(statistics.median(ps), 1); r = db.get(Rate, t)
    if r: r.price, r.updated, r.by_id = med, time.time(), uid
    else: db.add(Rate(type=t, price=med, by_id=uid))
    db.commit()

@router.get("/rates")
def rates(db: Session = Depends(get_db)):
    out = {k: {"price": v, "updated": None, "reports": 0} for k, v in RATES.items()}
    for r in db.scalars(select(Rate)): out[r.type] = {"price": r.price, "updated": r.updated if r.by_id else None, "reports": 0}
    by = {}
    for t, p in db.execute(select(RateReport.type, RateReport.price).where(RateReport.created > time.time() - 7 * 86400)): by.setdefault(t, []).append(p)
    for t, ps in by.items(): out[t].update(reports=len(ps), low=min(ps), high=max(ps))
    for k, (lo, hi) in REF.items(): out[k].update(ref_low=lo, ref_high=hi)
    out["_meta"] = {"ref_date": REF_DATE}
    return out

@router.put("/rates/{t}")
def report_rate(t: str, b: BidIn, u: User = Depends(require_verified_recycler), db: Session = Depends(get_db)):
    add_report(db, t, b.amount, u.id); return {"ok": True}

@router.post("/lots")
def add_lot(b: LotIn, u: User = Depends(require("collector")), db: Session = Depends(get_db)):
    check_pickup(b.pickup_date)
    l = Lot(id="KC" + uuid.uuid4().hex[:8].upper(), owner_id=u.id, type=b.type, kg=b.kg, city=b.city, lat=b.lat, lng=b.lng,
            address=b.address, pickup_date=b.pickup_date, pickup_slot=b.pickup_slot or ("morning" if b.pickup_date else None))
    db.add(l); db.commit(); return {"id": l.id, "suggested": round(price_of(db, b.type) * b.kg)}

@router.put("/lots/{lot}")
def edit_lot(lot: str, b: LotEdit, u: User = Depends(require("collector")), db: Session = Depends(get_db)):
    l = db.get(Lot, lot)
    if not l or l.owner_id != u.id: raise HTTPException(404, "Not your lot")
    if l.status != "open": raise HTTPException(409, "Only open lots can be edited")
    if db.scalar(select(func.count(Bid.id)).where(Bid.lot_id == lot)): raise HTTPException(409, "This lot already has bids. Cancel it and post again.")
    check_pickup(b.pickup_date)
    for k, v in b.model_dump(exclude_unset=True).items(): setattr(l, k, v)
    db.commit(); return {"ok": True}

@router.delete("/lots/{lot}")
def cancel_lot(lot: str, u: User = Depends(require("collector")), db: Session = Depends(get_db)):
    l = db.get(Lot, lot)
    if not l or l.owner_id != u.id: raise HTTPException(404, "Not your lot")
    if l.status != "open": raise HTTPException(409, "Only open lots can be cancelled")
    l.status = "cancelled"
    for (buyer,) in db.execute(select(Bid.buyer_id).where(Bid.lot_id == lot)): notify(db, buyer, "cancel", lot=lot, who=u.name)
    db.commit(); return {"ok": True}

@router.get("/lots")
def lots(u: User = Depends(current_user), db: Session = Depends(get_db)):
    if u.role == "collector":
        q = (select(Lot, func.count(Bid.id), func.max(Bid.amount)).outerjoin(Bid, Bid.lot_id == Lot.id)
             .where(Lot.owner_id == u.id).group_by(Lot.id).order_by(Lot.created.desc()))
        return [lot_d(l, n=n, best=m) for l, n, m in db.execute(q)]
    q = (select(Lot, Bid.amount, User.name, User.id).join(User, User.id == Lot.owner_id)
         .outerjoin(Bid, and_(Bid.lot_id == Lot.id, Bid.buyer_id == u.id)).where(Lot.status == "open").order_by(Lot.created.desc()).limit(100))
    return [lot_d(l, mine=m, seller=n, seller_id=i, seller_rating=rating_of(db, i)) for l, m, n, i in db.execute(q)]

@router.post("/lots/{lot}/bids")
def place_bid(lot: str, b: BidIn, u: User = Depends(require_verified_recycler), db: Session = Depends(get_db)):
    l = db.get(Lot, lot)
    if not l or l.status != "open": raise HTTPException(404, "Lot not open")
    x = db.scalar(select(Bid).where(Bid.lot_id == lot, Bid.buyer_id == u.id))
    if x: x.amount = b.amount
    else: db.add(Bid(lot_id=lot, buyer_id=u.id, amount=b.amount))
    notify(db, l.owner_id, "bid", lot=lot, amount=b.amount, who=u.name)
    db.commit(); return {"ok": True}

@router.get("/lots/{lot}/bids")
def lot_bids(lot: str, u: User = Depends(require("collector")), db: Session = Depends(get_db)):
    l = db.get(Lot, lot)
    if not l or l.owner_id != u.id: raise HTTPException(404, "Not your lot")
    q = select(Bid.id, Bid.amount, User.name, User.id).join(User, User.id == Bid.buyer_id).where(Bid.lot_id == lot).order_by(Bid.amount.desc())
    return [{"id": i, "amount": a, "buyer": n, "buyer_id": uid, "rating": rating_of(db, uid)} for i, a, n, uid in db.execute(q)]

@router.post("/bids/{bid}/accept")
def accept(bid: str, u: User = Depends(require("collector")), db: Session = Depends(get_db)):
    b = db.get(Bid, bid); l = db.get(Lot, b.lot_id) if b else None
    if not b or l.owner_id != u.id or l.status != "open": raise HTTPException(404, "Bid not available")
    l.status = "sold"; s = Sale(lot_id=l.id, seller_id=u.id, buyer_id=b.buyer_id, type=l.type, kg=l.kg, amount=b.amount); db.add(s); db.flush()
    notify(db, b.buyer_id, "sold", lot=l.id, amount=b.amount, who=u.name)
    db.commit(); return {"lot": l.id, "amount": b.amount, "sale": s.id}

@router.get("/ledger")
def ledger(u: User = Depends(current_user), db: Session = Depends(get_db)):
    mine = Sale.seller_id if u.role == "collector" else Sale.buyer_id
    rows = db.scalars(select(Sale).where(mine == u.id).order_by(Sale.created.desc())).all()
    people = {x.id: x for x in db.scalars(select(User).where(User.id.in_({r.seller_id for r in rows} | {r.buyer_id for r in rows})))} if rows else {}
    lots_ = {x.id: x for x in db.scalars(select(Lot).where(Lot.id.in_({r.lot_id for r in rows})))} if rows else {}
    rated = {x for (x,) in db.execute(select(Rating.sale_id).where(Rating.from_id == u.id))}
    out = []
    for r in rows:
        o = people.get(r.buyer_id if u.role == "collector" else r.seller_id); l = lots_.get(r.lot_id)
        out.append({"id": r.id, "lot": r.lot_id, "type": r.type, "kg": r.kg, "amount": r.amount, "created": r.created, "other": o.name if o else "", "other_phone": o.phone if o else "",
                    "rated": r.id in rated, "stage": r.stage or "scheduled", "pay_status": r.pay_status or "pending", "pay_method": r.pay_method, "pay_ref": r.pay_ref,
                    "city": l.city if l else "", "address": l.address if l else None, "lat": l.lat if l else None, "lng": l.lng if l else None,
                    "pickup_date": l.pickup_date if l else None, "pickup_slot": l.pickup_slot if l else None})
    total = sum(r.amount for r in rows); got = sum(r.amount for r in rows if r.pay_status == "confirmed")
    return {"total": total, "received": got, "pending": total - got, "sales": out}
