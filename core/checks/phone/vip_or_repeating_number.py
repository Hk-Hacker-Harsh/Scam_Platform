"""Number with long repeated digits (bought 'VIP' number often used by scam call centres)"""
import re
from ...engine import check


@check("vip_or_repeating_number", "Phone", "S", 10, "Number with long repeated digits (bought 'VIP' number often used by scam call centres)", needs="phones")
def vip_number(ctx):
    for p in ctx.ids["phones"]:
        if re.search(r"(\d)\1{4,}", p):
            return f"{p} has repeated digits"
