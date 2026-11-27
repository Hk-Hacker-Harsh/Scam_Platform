"""Reads SMS and contains UPI collect / payment strings: OTP theft paired with payment requests"""
from ...engine import check


@check("apk_sms_plus_upi_collect", "APK", "H", 40, "Reads SMS and builds UPI collect / payment requests (OTP theft paired with payment fraud)", needs="apk")
def sms_upi(ctx):
    a = ctx.apk
    if not ({"READ_SMS", "RECEIVE_SMS"} & set(a["perms"]) or "sms_read" in (a.get("api_refs") or [])):
        return None
    hits = [s for s in a["strings"] if "upi://" in s.lower() or "collect" in s.lower() and "upi" in s.lower()]
    return f"reads SMS and contains UPI request strings: {hits[0][:80]}" if hits else None
