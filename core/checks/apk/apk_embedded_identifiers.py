"""Phone numbers, UPI IDs, e-mails, raw IPs or Telegram bot tokens hard-coded in the app"""
from ...engine import check


@check("apk_embedded_identifiers", "APK", "S", 30, "Phone numbers, UPI IDs, e-mails, raw IPs or Telegram bot tokens hard-coded in the app", needs="apk")
def embedded_ids(ctx):
    ids = ctx.ids
    parts = []
    for k, lab in (("phones", "phone"), ("upis", "UPI ID"), ("emails", "e-mail"), ("ips", "IP"), ("tgbots", "Telegram bot token")):
        if ids.get(k):
            parts.append(f"{len(ids[k])} {lab}(s)")
    return "embedded " + ", ".join(parts) if parts else None
