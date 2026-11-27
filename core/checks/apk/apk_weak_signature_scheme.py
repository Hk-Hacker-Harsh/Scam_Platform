"""Only legacy v1 signature (no v2/v3)"""
from ...engine import check


@check("apk_weak_signature_scheme", "APK", "S", 10, "Only legacy v1 signature (no v2/v3)", needs="apk")
def weak_sig(ctx):
    v = ctx.apk["signed_v"]
    return "v1-only signature" if v == ["v1"] else None
