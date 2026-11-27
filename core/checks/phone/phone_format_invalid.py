"""Phone number has an impossible format for the country it claims"""
import re
from ...engine import check


@check("phone_format_invalid", "Phone", "S", 10, "Phone number has an impossible format for the country it claims", needs="phones")
def phone_format(ctx):
    bad = [p for p in ctx.ids["phones"] if p.startswith("+91") and not re.fullmatch(r"\+91[6-9]\d{9}", p) and not p.startswith("+911800")]
    return f"malformed Indian number {bad[0]}" if bad else None
