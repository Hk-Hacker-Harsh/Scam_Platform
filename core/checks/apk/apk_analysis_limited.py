"""Info: manifest could not be parsed; only string-level analysis was possible"""
from ...engine import check


@check("apk_analysis_limited", "APK", "L", 0, "Info: manifest could not be parsed; only string-level analysis was possible", needs="apk")
def limited(ctx):
    return ctx.apk["error"] if ctx.apk["limited"] else None
