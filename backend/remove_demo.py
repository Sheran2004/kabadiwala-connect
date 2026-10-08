"""Delete the DEMO accounts (9000000000-9000000003) and everything tied to them (sample lots, bids, sales, ratings, chats, rate reports).
Real users and their data are kept.  py -3.12 remove_demo.py     (add --yes to skip the question)"""
import statistics, sys, time
from sqlalchemy import select, delete, or_
from app.config import RATES
from app.database import SessionLocal
from app.models import User, Lot, Bid, Sale, Rate, RateReport, Notification, Otp, Rating, Message
DEMO = ("9000000000", "9000000001", "9000000002", "9000000003")
with SessionLocal() as db:
    ids = [u.id for u in db.scalars(select(User).where(User.phone.in_(DEMO)))]
    if not ids: sys.exit("No demo accounts found. Nothing to do.")
    if "--yes" not in sys.argv and input(f"This deletes {len(ids)} demo account(s) and all their data. Type YES to continue: ").strip() != "YES": sys.exit("Cancelled.")
    lots = [x for (x,) in db.execute(select(Lot.id).where(Lot.owner_id.in_(ids)))]
    sales = [x for (x,) in db.execute(select(Sale.id).where(or_(Sale.seller_id.in_(ids), Sale.buyer_id.in_(ids))))]
    db.execute(delete(Rating).where(or_(Rating.sale_id.in_(sales), Rating.from_id.in_(ids), Rating.to_id.in_(ids))))
    db.execute(delete(Message).where(or_(Message.lot_id.in_(lots), Message.sender_id.in_(ids), Message.receiver_id.in_(ids))))
    db.execute(delete(Bid).where(or_(Bid.lot_id.in_(lots), Bid.buyer_id.in_(ids))))
    db.execute(delete(Notification).where(Notification.user_id.in_(ids)))
    db.execute(delete(Sale).where(Sale.id.in_(sales))); db.execute(delete(Lot).where(Lot.id.in_(lots)))
    db.execute(delete(RateReport).where(RateReport.by_id.in_(ids))); db.execute(delete(Otp).where(Otp.phone.in_(DEMO)))
    db.execute(delete(User).where(User.id.in_(ids))); db.flush()
    for t, base in RATES.items():   # recompute each rate from the remaining (real) reports of the last 7 days
        ps = [p for (p,) in db.execute(select(RateReport.price).where(RateReport.type == t, RateReport.created > time.time() - 7 * 86400))]
        r = db.get(Rate, t)
        if r: r.price, r.by_id = (round(statistics.median(ps), 1), r.by_id) if ps else (base, None)
    db.commit(); print(f"Removed {len(ids)} demo accounts, {len(lots)} lots, {len(sales)} sales. Real users are untouched.")
