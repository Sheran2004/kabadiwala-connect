import json, urllib.parse
from app import config as C, sms

class _Resp:
    def __init__(self, d): self.d = d
    def read(self): return json.dumps(self.d).encode()

def _spy(monkeypatch, reply):
    seen = []
    monkeypatch.setattr(sms.urllib.request, "urlopen", lambda req, timeout=0: (seen.append(req), _Resp(reply))[1])
    return seen

def _cfg(monkeypatch, route, **kw):
    monkeypatch.setattr(C, "SMS_PROVIDER", "fast2sms"); monkeypatch.setattr(C, "FAST2SMS_KEY", "KEY123"); monkeypatch.setattr(C, "FAST2SMS_ROUTE", route)
    for k, v in kw.items(): monkeypatch.setattr(C, k, v)

def test_quick_sms_route(monkeypatch):
    _cfg(monkeypatch, "q"); seen = _spy(monkeypatch, {"return": True}); sms.send_otp("9876543210", "654321")
    r = seen[0]; f = dict(urllib.parse.parse_qsl(r.data.decode()))
    assert r.full_url.endswith("/dev/bulkV2") and r.get_header("Authorization") == "KEY123" and f["route"] == "q" and f["numbers"] == "9876543210" and "654321" in f["message"]

def test_old_otp_route(monkeypatch):
    _cfg(monkeypatch, "otp"); seen = _spy(monkeypatch, {"return": True}); sms.send_otp("9876543210", "654321")
    assert dict(urllib.parse.parse_qsl(seen[0].data.decode())) == {"variables_values": "654321", "route": "otp", "numbers": "9876543210"}

def test_managed_otp_api(monkeypatch):
    _cfg(monkeypatch, "otp_api", FAST2SMS_OTP_ID="777"); assert sms.is_managed()
    seen = _spy(monkeypatch, {"return": True}); sms.send_managed("9876543210")
    assert seen[0].full_url.endswith("/dev/otp/send") and json.loads(seen[0].data) == {"otp_id": "777", "mobile": "9876543210"}
    assert sms.verify_managed("9876543210", "123456") is True and seen[1].full_url.endswith("/dev/otp/verify")
    _spy(monkeypatch, {"return": False}); assert sms.verify_managed("9876543210", "000000") is False

def test_provider_refusal_is_an_error(monkeypatch):
    _cfg(monkeypatch, "q"); _spy(monkeypatch, {"return": False, "message": "Insufficient balance"})
    try: sms.send_otp("9876543210", "111111"); assert False
    except RuntimeError as e: assert "Insufficient balance" in str(e)

def test_managed_flow_end_to_end(api, monkeypatch):
    _cfg(monkeypatch, "otp_api", FAST2SMS_OTP_ID="777"); sent = []
    monkeypatch.setattr(sms, "send_managed", lambda p: sent.append(p)); monkeypatch.setattr(sms, "verify_managed", lambda p, c: c == "424242")
    r = api.post("/auth/otp/request", json={"phone": "9111111150"}).json(); assert r["sent"] and r["dev_code"] is None and sent == ["9111111150"]
    body = {"phone": "9111111150", "name": "Managed User", "password": "password1", "role": "collector", "code": "000000"}
    assert api.post("/auth/register", json=body).status_code == 400
    body["code"] = "424242"; assert api.post("/auth/register", json=body).status_code == 200
