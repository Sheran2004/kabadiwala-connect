"""Create a REAL admin (or reset an admin's password).
   py -3.12 create_admin.py --phone 98xxxxxxxx --name "Your Name"      (the password is asked; or set ADMIN_PASSWORD)"""
import argparse, getpass, os, sys
from sqlalchemy import select
from app.database import Base, engine, SessionLocal, migrate
from app.models import User
from app.security import new_salt, hash_pw
WEAK = {"admin12345", "password", "12345678", "admin@123", "password123", "1234567890"}
ap = argparse.ArgumentParser(); ap.add_argument("--phone", required=True); ap.add_argument("--name", default="Admin"); a = ap.parse_args()
if not (a.phone.isdigit() and len(a.phone) == 10): sys.exit("Phone must be 10 digits")
pw = os.getenv("ADMIN_PASSWORD")
if not pw:
    pw = getpass.getpass("New admin password (min 10 characters): ")
    if pw != getpass.getpass("Repeat password: "): sys.exit("Passwords do not match")
if len(pw) < 10 or pw.lower() in WEAK: sys.exit("Password too weak: use at least 10 characters and nothing common")
Base.metadata.create_all(engine); migrate()
with SessionLocal() as db:
    u = db.scalar(select(User).where(User.phone == a.phone)); s = new_salt()
    if u and u.role != "admin": sys.exit("This phone already belongs to a collector/recycler account. Use a different number for the admin.")
    if u: u.salt, u.pw_hash = s, hash_pw(pw, s); print("Admin password reset for", a.phone)
    else: db.add(User(phone=a.phone, name=a.name, role="admin", salt=s, pw_hash=hash_pw(pw, s), verified=True)); print("Admin created:", a.phone)
    db.commit()
