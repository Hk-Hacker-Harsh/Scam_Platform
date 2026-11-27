"""UPI ID embeds a bank/government/brand name (real merchants rarely do; scammers do)"""
import re
from ...engine import check


@check("upi_brand_in_id", "Payment", "H", 35, "UPI ID embeds a bank/government/brand name (real merchants rarely do; scammers do)", needs="upis")
def upi_brand(ctx):
    out = []
    for u in ctx.ids["upis"]:
        local = u.split("@")[0]
        b = re.search(r"(?i)(sbi|hdfc|icici|axis|rbi|npci|paytm|irctc|epfo|refund|kyc|support|care|helpdesk|police|cbi|govt|gov)", local)
        if b:
            out.append(f"{u} contains '{b.group(1)}'")
    return out
