"""Signing certificate is not issued to the brand the app pretends to be"""
from ...engine import check
from ..url.common import _brand_in


@check("apk_cert_brand_mismatch", "APK", "H", 35, "Signing certificate is not issued to the brand the app pretends to be", needs="apk")
def cert_mismatch(ctx):
    a = ctx.apk
    b = _brand_in(a["label"] or a["package"])
    subj = (a["cert"].get("subject") or "").lower()
    if b and subj and b.replace(" ", "") not in subj.replace(" ", ""):
        return f"app claims {b}; certificate subject is '{a['cert']['subject'][:60]}'"
