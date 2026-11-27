"""Dangerous permission combination typical of banking trojans / stalkerware"""
from ...engine import check


@check("apk_permission_combo", "APK", "H", 45, "Dangerous permission combination typical of banking trojans / stalkerware", needs="apk")
def perm_combo(ctx):
    # uses-permission entries plus permissions that guard components (an accessibility service declares
    # BIND_ACCESSIBILITY_SERVICE on the <service>, not as a uses-permission)
    p = set(ctx.apk["perms"]) | set(ctx.apk.get("component_perms") or [])
    out = []
    if {"READ_SMS", "INTERNET"} <= p or {"RECEIVE_SMS", "INTERNET"} <= p and "READ_SMS" in p:
        out.append("reads SMS + internet (OTP theft)")
    if "BIND_ACCESSIBILITY_SERVICE" in p:
        out.append("accessibility service (screen control)")
    if "SYSTEM_ALERT_WINDOW" in p and ("READ_SMS" in p or "BIND_ACCESSIBILITY_SERVICE" in p):
        out.append("screen overlay + SMS/accessibility (fake login overlays)")
    if "BIND_DEVICE_ADMIN" in p:
        out.append("device admin (hard to uninstall)")
    if {"READ_CONTACTS", "READ_CALL_LOG"} <= p and "INTERNET" in p:
        out.append("contacts + call log exfiltration")
    if "REQUEST_INSTALL_PACKAGES" in p and "READ_SMS" in p:
        out.append("can install other apps + reads SMS (dropper)")
    return "; ".join(out) or None
