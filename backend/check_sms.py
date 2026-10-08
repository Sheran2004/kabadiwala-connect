"""Test your SMS setup.   py -3.12 check_sms.py 9876543210 [--route q|otp|otp_api]
Sends ONE test SMS with the provider from backend/.env (a real SMS costs credits). Prints exactly what Fast2SMS answered."""
import sys
from app import config as C, sms
args = [a for a in sys.argv[1:] if not a.startswith("--")]
if "--route" in sys.argv: C.FAST2SMS_ROUTE = sys.argv[sys.argv.index("--route") + 1]; args = [a for a in args if a != C.FAST2SMS_ROUTE]
if not args or not (args[0].isdigit() and len(args[0]) == 10): raise SystemExit("Usage: py -3.12 check_sms.py <10-digit phone> [--route q|otp|otp_api]")
ph = args[0]; print("SMS_PROVIDER:", C.SMS_PROVIDER, "| route:", C.FAST2SMS_ROUTE if C.SMS_PROVIDER == "fast2sms" else "-", "| FAST2SMS_KEY:", "set" if C.FAST2SMS_KEY else "MISSING")
try:
    if sms.is_managed():
        sms.send_managed(ph); got = input("OTP sent. Type the OTP you received (or press Enter to skip): ").strip()
        if got: print("Verify:", "OK" if sms.verify_managed(ph, got) else "WRONG OTP")
    else:
        sms.send_otp(ph, "123456"); print("(console provider: nothing real was sent)" if C.SMS_PROVIDER == "console" else "OK - Fast2SMS accepted the request. The SMS (test OTP 123456) can take up to a minute.")
except Exception as e:
    print("FAILED:", e); print("\nRead the message above. Common reasons: wallet empty / minimum recharge not done, account or website not verified, wrong key, number on DND, or this route is not enabled for your account.\nTry another route:  --route q   --route otp   --route otp_api (needs FAST2SMS_OTP_ID)")
