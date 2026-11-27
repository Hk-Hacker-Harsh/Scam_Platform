"""Attachment type commonly used to deliver malware (.apk, .exe, .scr, .html, .iso, .js, .lnk)"""
import re
from ...engine import check


@check("email_risky_attachment", "Email", "H", 35, "Attachment type commonly used to deliver malware (.apk, .exe, .scr, .html, .iso, .js, .lnk)", needs="headers")
def risky_attach(ctx):
    names = []
    for part in ctx.headers.walk():
        fn = part.get_filename()
        if fn:
            names.append(fn)
    bad = [n for n in names if re.search(r"(?i)\.(apk|exe|scr|bat|cmd|js|jse|vbs|lnk|iso|img|html?|hta|jar|msi|docm|xlsm|zip|rar)$", n)]
    return "attachment(s): " + ", ".join(bad[:3]) if bad else None
