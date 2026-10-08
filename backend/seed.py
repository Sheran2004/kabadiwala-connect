"""Demo accounts (password demo12345) + admin (9000000000 / admin12345). Run: py -3.12 seed.py
Demo only - in production create the admin with ADMIN_PHONE / ADMIN_PASSWORD env vars instead."""
from sqlalchemy import select
from app.database import Base, engine, SessionLocal, migrate
from app.models import User
from app.security import new_salt, hash_pw
Base.metadata.create_all(engine); migrate()
with SessionLocal() as db:
    for p, n, r, pw in [("9000000001", "Ramu Kabadiwala", "collector", "demo12345"), ("9000000002", "EcoCycle Hub", "recycler", "demo12345"),
                        ("9000000003", "Sharma Metals", "recycler", "demo12345"), ("9000000000", "Admin", "admin", "admin12345")]:
        u = db.scalar(select(User).where(User.phone == p))
        if u: u.verified = u.verified or r != "collector"; print(p, "exists (verified)"); continue
        s = new_salt(); db.add(User(phone=p, name=n, role=r, salt=s, pw_hash=hash_pw(pw, s), verified=r != "collector")); print(p, n, r, "created")
    db.commit()
