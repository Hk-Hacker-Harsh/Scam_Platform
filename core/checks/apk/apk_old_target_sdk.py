"""Targets an old Android API level (<28) to dodge modern permission protections"""
from ...engine import check


@check("apk_old_target_sdk", "APK", "S", 20, "Targets an old Android API level (<28) to dodge modern permission protections", needs="apk")
def old_sdk(ctx):
    t = ctx.apk["target_sdk"]
    return f"targetSdkVersion {t}" if t is not None and t < 28 else None
