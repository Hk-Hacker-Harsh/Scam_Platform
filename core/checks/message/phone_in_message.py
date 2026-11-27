"""Message pushes you to call/WhatsApp an unknown number"""
import re
from ...engine import check


@check("phone_in_message", "Message", "S", 15, "Message pushes you to call/WhatsApp an unknown number", needs="phones")
def phone_in_msg(ctx):
    if ctx.kind in ("message", "email") and re.search(r"(?i)(call|contact|whatsapp|dial|helpline|customer care|support)", ctx.text):
        return f"{len(ctx.ids['phones'])} number(s) given to contact: {', '.join(ctx.ids['phones'][:3])}"
