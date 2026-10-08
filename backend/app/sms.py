import base64, json, urllib.error, urllib.parse, urllib.request
from . import config as C
BULK = "https://www.fast2sms.com/dev/bulkV2"; OTP_SEND = "https://www.fast2sms.com/dev/otp/send"; OTP_VERIFY = "https://www.fast2sms.com/dev/otp/verify"

def is_managed(): return C.SMS_PROVIDER == "fast2sms" and C.FAST2SMS_ROUTE == "otp_api"

def _f2s(url, data, as_json=False, soft=False):
    if not C.FAST2SMS_KEY: raise RuntimeError("FAST2SMS_KEY is not set")
    body = json.dumps(data).encode() if as_json else urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, body, {"authorization": C.FAST2SMS_KEY, "accept": "application/json", "User-Agent": "KabadiwalaConnect/1.0",
                                              "Content-Type": "application/json" if as_json else "application/x-www-form-urlencoded"})
    try: return json.loads(urllib.request.urlopen(req, timeout=20).read())
    except urllib.error.HTTPError as e:
        txt = e.read().decode()[:200]
        if soft and e.code in (400, 404, 422): return {"return": False, "message": txt}
        raise RuntimeError(f"Fast2SMS HTTP {e.code}: {txt}")

def _need_ok(r):
    if not r.get("return"): raise RuntimeError(f"Fast2SMS refused: {r.get('message')}")

def send_otp(phone: str, code: str):
    """We create the code. console (dev) | fast2sms route q (Quick SMS) or otp (old OTP route) | twilio."""
    p = C.SMS_PROVIDER
    if p == "fast2sms":
        if C.FAST2SMS_ROUTE == "otp": _need_ok(_f2s(BULK, {"variables_values": code, "route": "otp", "numbers": phone}))
        else: _need_ok(_f2s(BULK, {"route": "q", "message": f"Your Kabadiwala Connect OTP is {code}. Valid for 5 minutes. Do not share it.", "numbers": phone}))
        return
    if p == "twilio":
        data = urllib.parse.urlencode({"To": "+91" + phone, "From": C.TWILIO_FROM, "Body": f"Kabadiwala Connect OTP: {code}. Valid for 5 minutes. Do not share it."}).encode()
        auth = base64.b64encode(f"{C.TWILIO_SID}:{C.TWILIO_TOKEN}".encode()).decode()
        urllib.request.urlopen(urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{C.TWILIO_SID}/Messages.json", data, {"Authorization": "Basic " + auth}), timeout=20).read(); return
    print(f"\n[OTP] SMS to {phone}: Kabadiwala Connect OTP {code} (valid 5 min)\n", flush=True)   # console provider

def send_managed(phone: str):
    if not C.FAST2SMS_OTP_ID: raise RuntimeError("FAST2SMS_OTP_ID is not set (needed for FAST2SMS_ROUTE=otp_api)")
    _need_ok(_f2s(OTP_SEND, {"otp_id": C.FAST2SMS_OTP_ID, "mobile": phone}, as_json=True))

def verify_managed(phone: str, code: str) -> bool:
    return bool(_f2s(OTP_VERIFY, {"mobile": phone, "otp": code}, as_json=True, soft=True).get("return"))
