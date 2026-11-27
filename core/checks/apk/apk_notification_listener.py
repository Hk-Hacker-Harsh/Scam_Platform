"""Notification-listener service: can read every notification, including bank OTPs"""
from ...engine import check


@check("apk_notification_listener", "APK", "S", 25, "Has a notification-listener service, so it can read every notification including bank OTPs", needs="apk")
def notif(ctx):
    a = ctx.apk
    if "BIND_NOTIFICATION_LISTENER_SERVICE" in (a.get("component_perms") or []):
        return "declares a NotificationListenerService" + (" and has internet access" if "INTERNET" in a["perms"] else "")
