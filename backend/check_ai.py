"""Run from the backend folder:  py -3.12 check_ai.py
Tests your keys, finds working models and prints exactly what is wrong (if anything)."""
from fastapi import HTTPException
from app import config as C
from app.routers import ai

mask = lambda k: "MISSING" if not k else f"{k[:4]}...{k[-3:]} (length {len(k)})"
print("GROQ_API_KEY  :", mask(C.GROQ_API_KEY)); print("GEMINI_API_KEY:", mask(C.GEMINI_API_KEY))
if not (C.GROQ_API_KEY or C.GEMINI_API_KEY): print("\nNo key found. Put GROQ_API_KEY=... in backend/.env, save, run again.")
ask = [{"role": "user", "content": "Say hi in one word"}]
if C.GROQ_API_KEY:
    print("\n[Groq]")
    try:
        print(" reply:", ai.groq(ask)); print(" model used:", ai._auto.get("groq", C.GROQ_MODEL))
        if "groq_list" in ai._auto: print(" (configured model was retired; models on your key:", ", ".join(ai._auto["groq_list"]), ")")
    except HTTPException as e: print(" FAILED:", e.detail, "\n 401=bad key, 403=blocked network/key, 429=quota, unreachable=internet/VPN problem")
if C.GEMINI_API_KEY:
    print("\n[Gemini]")
    try:
        print(" reply:", ai.gemini({"contents": [{"parts": [{"text": "Say hi in one word"}]}]})); print(" model used:", ai._auto.get("gemini", C.GEMINI_MODEL))
        if "gemini_list" in ai._auto: print(" (configured model was retired; flash models on your key:", ", ".join(ai._auto["gemini_list"][:6]), ")")
    except HTTPException as e: print(" FAILED:", e.detail)
