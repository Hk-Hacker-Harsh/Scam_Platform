"""App contains a Telegram bot token / API endpoint (common SMS and data exfiltration channel)"""
from ...engine import check


@check("apk_telegram_exfil", "APK", "H", 45, "App contains a Telegram bot token / API endpoint (common SMS and data exfiltration channel)", needs="apk")
def tg_exfil(ctx):
    if ctx.ids.get("tgbots") or any("api.telegram.org" in s.lower() for s in ctx.apk["strings"]):
        return "Telegram bot API found in app code"
