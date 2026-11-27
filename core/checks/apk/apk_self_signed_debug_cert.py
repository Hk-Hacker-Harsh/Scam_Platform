"""Signed with a debug or self-signed certificate (not a real publisher identity)"""
import re
from ...engine import check


@check("apk_self_signed_debug_cert", "APK", "S", 30, "Signed with a debug or self-signed certificate (not a real publisher identity)", needs="apk")
def self_signed(ctx):
    c = ctx.apk["cert"]
    if not c:
        return "no readable signing certificate" if not ctx.apk["limited"] else None
    s = (c.get("subject") or "").lower()
    if "android debug" in s:
        return "signed with the Android debug certificate"
    if c.get("self_signed") and not re.search(r"(?i)\bO=|organization", c.get("subject", "")):
        return f"self-signed certificate with no organisation ({c['subject'][:50]})"
