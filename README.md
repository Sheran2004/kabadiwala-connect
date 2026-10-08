# Kabadiwala Connect v5 (SIH26229)
Kabadiwalas sell scrap, recyclers bid, the deal is tracked to pickup and payment.  backend/ FastAPI + SQLAlchemy (SQLite locally, PostgreSQL in production) | frontend/ HTML/CSS/JS PWA

## Features
OTP register/login (+ password, forgot/change password) | admin approval of recyclers | lots with map pin + pickup slot | bids, chat, ratings
| order tracking (scheduled > on the way > picked up) and payment confirmation (buyer: sent, seller: received) | rates = median of recycler reports (starting values from published rate cards)
| Groq/Gemini chatbot, voice input, AI photo scan | Hindi/English, dark/light, installable PWA, offline shell | login rate-limit, security headers, automated tests (pytest + GitHub Actions)

## Run locally (Windows PowerShell, two terminals)
    cd backend ; py -3.12 -m pip install -r requirements.txt
    copy .env.example .env             (add AI keys; keep KC_DEBUG_OTP=1 for local OTP)
    py -3.12 -m uvicorn app.main:app --reload --port 8000
    cd frontend ; py -3.12 -m http.server 5500      -> http://localhost:5500   (config.js holds the API address)

## Real accounts only (no demo data)
    py -3.12 create_admin.py --phone 98xxxxxxxx --name "Your Name"    # your real admin (password is asked)
    py -3.12 remove_demo.py                                           # deletes the demo accounts + sample data (real users are kept)
Collectors and recyclers register themselves with an OTP. The admin approves recyclers in the Recyclers tab.
(Demo only: `seed.py` creates demo accounts, `seed_demo.py` adds sample data. Never run them on a live server.)

## OTP on a real phone
Set SMS_PROVIDER=fast2sms and FAST2SMS_KEY in backend/.env, restart, test: `py -3.12 check_sms.py 98xxxxxxxx`. Remove KC_DEBUG_OTP afterwards.
SMS in India needs a paid/verified gateway account; check the provider's current rules, wallet and DND limits.

## Tests
    py -3.12 -m pip install -r backend/requirements-dev.txt ; py -3.12 -m pytest backend/tests -q

## Deploy: see DEPLOY.md (GitHub + Neon Postgres + Render). Tested on SQLite and PostgreSQL 16.
## Known limits
Rates are indicative until recyclers report real prices | "approved recycler" = admin's manual check (no KYC documents) | chat polls every 5 s | rate-limit is in-memory (one server)
| login sessions last 7 days and are not revoked on password change | no online payments: payment is a confirmation step only
