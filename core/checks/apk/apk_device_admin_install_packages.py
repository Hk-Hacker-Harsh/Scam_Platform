"""Device-admin rights (hard to uninstall) or permission to install other apps"""
from ...engine import check


@check("apk_device_admin_install_packages", "APK", "S", 20, "Asks for device-admin rights (hard to uninstall) or can install other apps", needs="apk")
def admin(ctx):
    a = ctx.apk
    caps = set(a["perms"]) | set(a.get("component_perms") or [])
    out = []
    if "BIND_DEVICE_ADMIN" in caps:
        out.append("device administrator receiver")
    if "REQUEST_INSTALL_PACKAGES" in caps:
        out.append("REQUEST_INSTALL_PACKAGES (can install other apps)")
    return out or None
