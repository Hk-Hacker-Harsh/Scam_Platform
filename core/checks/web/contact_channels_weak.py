"""Only free-mail / WhatsApp / Telegram contact; no address, phone landline or grievance officer"""
import re
from ...engine import check
from .common import _soup


@check("contact_channels_weak", "Website", "S", 20, "Only free-mail / WhatsApp / Telegram contact; no address, phone landline or grievance officer", needs="html")
def weak_contact(ctx):
    t = _soup(ctx).get_text(" ", strip=True).lower()
    free = re.search(r"@(gmail|yahoo|outlook|hotmail|rediffmail)\.", ctx.html, re.I)
    chat = re.search(r"wa\.me/|t\.me/|whatsapp|telegram", ctx.html, re.I)
    addr = re.search(r"(address|registered office|head office|grievance|nodal officer)", t)
    if (free or chat) and not addr:
        return "contact only via free e-mail / chat app, no registered address or grievance officer"
