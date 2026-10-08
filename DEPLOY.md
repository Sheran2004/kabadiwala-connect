# 1) GitHub (from the project folder, in the VS Code terminal)
Create an EMPTY repo on github.com first (no README / .gitignore / license), then:
    git init
    git add .
    git status                          # must NOT list .env, *.db or .jwt_secret
    git grep -nE "gsk_|AIza|AQ\.A|BEGIN PRIVATE KEY"      # must print nothing
    git commit -m "Kabadiwala Connect v5.0 - SIH26229 MVP"
    git branch -M main
    git remote add origin https://github.com/<your-username>/kabadiwala-connect.git
    git push -u origin main
If .env was staged by mistake: `git rm --cached backend/.env`, commit again, and ROTATE the keys that were in it.

# 2) Database: Neon (free Postgres, does not expire)  -> neon.tech
Sign up > Create project > copy the connection string (postgresql://user:pass@host/db?sslmode=require). Check Neon's current free limits.
(Render's own free Postgres is deleted 30 days after creation, so it is not used here.)

# 3) Hosting: Render (API + website, both free)  -> render.com
1. New > Blueprint > connect GitHub > pick the repo. It creates `kabadiwala-api` (Docker) and `kabadiwala-web` (static) from render.yaml.
2. When asked for values, fill: DATABASE_URL (Neon string) | GROQ_API_KEY, GEMINI_API_KEY | ADMIN_PHONE + ADMIN_PASSWORD (your real admin) | leave KC_ORIGINS and KC_API_URL empty for now | FAST2SMS_KEY empty.
3. After the first deploy copy the two URLs, then set:  API > KC_ORIGINS = website URL | Website > KC_API_URL = API URL (no trailing slash).
4. Re-deploy both (website must rebuild: it writes config.js from KC_API_URL).
5. Open the website URL, log in with ADMIN_PHONE / ADMIN_PASSWORD, approve recyclers in the Recyclers tab. Others register with an OTP (shown on screen in demo mode).
Free limits: the API sleeps after ~15 idle minutes (open the site 2 minutes before a demo to wake it). Free services have usage limits - check Render's current free plan.
Real SMS later: recharge Fast2SMS, set SMS_PROVIDER=fast2sms + FAST2SMS_KEY, delete KC_DEBUG_OTP, test with `py -3.12 check_sms.py`.
