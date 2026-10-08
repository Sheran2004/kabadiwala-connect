import os, secrets, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass
_k = lambda n: os.getenv(n, "").strip().strip("\"'")
ENV = _k("KC_ENV") or "development"; PROD = ENV == "production"
_db = _k("DATABASE_URL") or f"sqlite:///{ROOT / 'kabadiwala.db'}"
if _db.startswith("postgres://"): _db = _db.replace("postgres://", "postgresql+psycopg2://", 1)   # Render/Heroku style URLs
elif _db.startswith("postgresql://"): _db = _db.replace("postgresql://", "postgresql+psycopg2://", 1)
DATABASE_URL = _db
ORIGINS = [o.strip() for o in (_k("KC_ORIGINS") or "*").split(",")]
# Starting rates (Rs/kg): median of published kabadi rate cards for Delhi NCR / other cities, collected Oct 2026
# (thekabadiwala.com, kabadiwalaonline.in, kabadidost.in, urbanscrap.co, yourskabadi.com, scrapbuddy.in, kabadiwalaranchi.com).
# Indicative only - real rates differ by city and quality. Recyclers on the platform replace them with reported prices.
RATES = {"paper": 13, "card": 7, "pet": 12, "iron": 27, "alu": 115, "brass": 380, "cu": 550, "glass": 2, "ew": 20}
REF = {"paper": (12, 18), "card": (5, 8), "pet": (8, 30), "iron": (24, 42), "alu": (95, 170), "brass": (315, 500), "cu": (430, 750)}  # published ranges; glass and e-waste: no reliable range found
REF_DATE = "Oct 2026"

def _secret():
    s = _k("KC_JWT_SECRET")
    if s: return s
    if PROD: raise RuntimeError("KC_JWT_SECRET must be set when KC_ENV=production")
    f = ROOT / ".jwt_secret"  # dev convenience only. In production set KC_JWT_SECRET.
    if not f.exists(): f.write_text(secrets.token_hex(32))
    return f.read_text().strip()
SECRET = _secret()

GROQ_API_KEY = _k("GROQ_API_KEY"); GROQ_MODEL = _k("GROQ_MODEL") or "llama-3.3-70b-versatile"
GEMINI_API_KEY = _k("GEMINI_API_KEY"); GEMINI_MODEL = _k("GEMINI_MODEL") or "gemini-2.5-flash"
# OTP / SMS
SMS_PROVIDER = _k("SMS_PROVIDER") or "console"          # console (prints OTP in the backend terminal) | fast2sms (India) | twilio
FAST2SMS_KEY = _k("FAST2SMS_KEY")
FAST2SMS_ROUTE = _k("FAST2SMS_ROUTE") or "q"      # q = Quick SMS (our own OTP text) | otp = old OTP route | otp_api = Fast2SMS generates + verifies the OTP
FAST2SMS_OTP_ID = _k("FAST2SMS_OTP_ID")           # only for otp_api (from the Smart OTP panel)
DEBUG_OTP = _k("KC_DEBUG_OTP") == "1"                    # returns the OTP in the API response. NEVER enable in production.
TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM = _k("TWILIO_SID"), _k("TWILIO_TOKEN"), _k("TWILIO_FROM")
