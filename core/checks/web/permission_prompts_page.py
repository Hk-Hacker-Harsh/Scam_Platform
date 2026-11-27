"""Page asks for camera, location, contacts, notifications or clipboard on load"""
import re
from ...engine import check


@check("permission_prompts_page", "Website", "S", 20, "Page asks for camera, location, contacts, notifications or clipboard on load", needs="html")
def perms(ctx):
    hits = re.findall(r"(?i)navigator\.(geolocation|mediaDevices|clipboard)|Notification\.requestPermission|contacts\.select", ctx.html)
    return "requests browser permissions: " + ", ".join(sorted({h if isinstance(h, str) else 'api' for h in hits}))[:60] if hits else None
