"""Unusually many dangerous permissions for a simple app"""
from ...engine import check
from ...data import DANGEROUS_PERMS


@check("apk_permission_count", "APK", "S", 20, "Unusually many dangerous permissions for a simple app", needs="apk")
def perm_count(ctx):
    n = len(DANGEROUS_PERMS & set(ctx.apk["perms"]))
    return f"{n} dangerous permissions" if n >= 8 else None
