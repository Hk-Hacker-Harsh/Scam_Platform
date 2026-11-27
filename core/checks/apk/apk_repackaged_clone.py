"""App is named like a bank/government/payment brand but its package name is not that brand's real package"""
from ...engine import check
from ...data import BRANDS
from ..url.common import _brand_in


@check("apk_repackaged_clone", "APK", "H", 45, "App is named like a bank/government/payment brand but its package name is not that brand's real package", needs="apk")
def clone(ctx):
    a = ctx.apk
    name = (a["label"] + " " + a["package"]).lower()
    b = _brand_in(a["label"] or "") or _brand_in(a["package"].replace(".", " ") if a["package"] else "")
    if not b:
        return
    real = BRANDS.get(b, {}).get("packages", [])
    if a["package"] and a["package"] not in real:
        return f"looks like {b} (label '{a['label']}') but package is {a['package']}"
