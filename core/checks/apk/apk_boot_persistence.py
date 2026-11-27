"""Starts automatically at boot together with sensitive permissions"""
from ...engine import check


@check("apk_boot_persistence", "APK", "S", 15, "Starts automatically at boot together with sensitive permissions", needs="apk")
def boot(ctx):
    p = set(ctx.apk["perms"])
    return "RECEIVE_BOOT_COMPLETED with SMS/contacts access" if "RECEIVE_BOOT_COMPLETED" in p and p & {"READ_SMS", "READ_CONTACTS", "RECORD_AUDIO"} else None
