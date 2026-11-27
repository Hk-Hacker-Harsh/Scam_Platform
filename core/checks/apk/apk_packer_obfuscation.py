"""Commercial packer / protector libraries that hide the real code from analysis"""
from ...engine import check


@check("apk_packer_obfuscation", "APK", "S", 20, "Packed with a protector library that hides the real code from static analysis", needs="apk")
def packer(ctx):
    p = ctx.apk.get("packers") or []
    return ("packer libraries: " + ", ".join(p[:4])) if p else None
