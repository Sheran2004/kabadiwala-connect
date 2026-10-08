import os, sys, tempfile, pathlib
_d = tempfile.mkdtemp()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_d}/test.db")
os.environ.update(KC_DEBUG_OTP="1", KC_JWT_SECRET="test-secret", ADMIN_PHONE="9000000000", ADMIN_PASSWORD="admin-pass-123", KC_ENV="development")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from app.main import app
from app.database import SessionLocal
from app.models import Otp
from app import ratelimit

@pytest.fixture()
def api():
    ratelimit.by_phone.h.clear(); ratelimit.by_ip.h.clear()
    c = TestClient(app)
    def H(tok): return {"Authorization": "Bearer " + tok}
    def register(phone, name, role, pw="password1"):
        code = c.post("/auth/otp/request", json={"phone": phone}).json()["dev_code"]
        return c.post("/auth/register", json={"phone": phone, "name": name, "password": pw, "role": role, "code": code}).json()
    def login(phone, pw): return c.post("/auth/login", json={"phone": phone, "password": pw}).json()
    def skip_cd(phone):
        with SessionLocal() as db: db.execute(update(Otp).where(Otp.phone == phone).values(created=Otp.created - 60)); db.commit()
    c.H, c.register, c.login, c.skip_cd = H, register, login, skip_cd
    return c
