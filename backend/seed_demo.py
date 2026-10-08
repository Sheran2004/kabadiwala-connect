"""OPTIONAL sample data for presentations (clearly sample, NOT real users). Run once after seed.py:  py -3.12 seed_demo.py
Creates a few sample lots with map pins, bids, finished sales, ratings and recycler rate reports near the published ranges.
Do NOT run this on a production server."""
import time, datetime, random
from sqlalchemy import select, func
from app.database import SessionLocal
from app.models import User, Lot, Bid, Sale, Rating
from app.routers.market import add_report, price_of
random.seed(7)
with SessionLocal() as db:
    if db.scalar(select(func.count(Lot.id))): raise SystemExit("Lots already exist - not adding sample data.")
    col = db.scalar(select(User).where(User.phone == "9000000001")); recs = [db.scalar(select(User).where(User.phone == p)) for p in ("9000000002", "9000000003")]
    if not col or not all(recs): raise SystemExit("Run seed.py first.")
    today = datetime.date.today()
    for t, ps in {"cu": (545, 560, 550), "alu": (112, 118, 115), "iron": (26, 28, 27), "paper": (13, 13, 14), "pet": (11, 12, 13), "brass": (370, 385, 380)}.items():
        for i, p in enumerate(ps): add_report(db, t, p, recs[i % 2].id)
    # (type, kg, city, lat, lng, address, days ahead, slot)
    lots = [("iron", 80, "Lucknow", 26.8467, 80.9462, "Hazratganj", 1, "morning"), ("paper", 45, "Lucknow", 26.8089, 80.9000, "Alambagh", 2, "afternoon"),
            ("alu", 12, "Lucknow", 26.8754, 80.9970, "Indira Nagar", 1, "evening"), ("cu", 6, "Noida", 28.6270, 77.3649, "Sector 62", 3, "morning"),
            ("pet", 30, "Lucknow", 26.7606, 80.8890, "Aliganj", 2, "morning"), ("brass", 4, "Lucknow", 26.9124, 80.9500, "Gomti Nagar", 4, "afternoon")]
    for i, (t, kg, city, la, ln, ad, d, sl) in enumerate(lots):
        l = Lot(id=f"KCDEMO{i+1:02d}", owner_id=col.id, type=t, kg=kg, city=city, lat=la, lng=ln, address=ad, pickup_date=(today + datetime.timedelta(days=d)).isoformat(), pickup_slot=sl)
        db.add(l); db.flush()
        for j, r in enumerate(recs):
            if (i + j) % 3 != 2: db.add(Bid(lot_id=l.id, buyer_id=r.id, amount=round(price_of(db, t) * kg * (0.93 + 0.05 * j + 0.02 * (i % 3)))))
    for t, kg, k in (("iron", 120, 0), ("paper", 60, 1), ("alu", 9, 0)):   # finished sales so Home / Ledger have numbers
        amt = round(price_of(db, t) * kg * 0.97); l = Lot(id=f"KCDONE{k}{t[:2].upper()}", owner_id=col.id, type=t, kg=kg, city="Lucknow", status="sold", created=time.time() - 86400 * (k + 3)); db.add(l); db.flush()
        s = Sale(lot_id=l.id, seller_id=col.id, buyer_id=recs[k].id, type=t, kg=kg, amount=amt, created=l.created + 3600, stage="picked_up", stage_at=l.created + 7200, pay_status="confirmed", pay_method=("cash", "upi", "cash")[k], pay_at=l.created + 9000); db.add(s); db.flush()
        db.add(Rating(sale_id=s.id, from_id=col.id, to_id=recs[k].id, stars=5 - k, comment="Time par aaye, sahi tol")); db.add(Rating(sale_id=s.id, from_id=recs[k].id, to_id=col.id, stars=5, comment="Maal saaf aur sorted tha"))
    db.commit(); print("Sample data added: 6 open lots with pins, bids, 3 finished sales, ratings, recycler rate reports.")
