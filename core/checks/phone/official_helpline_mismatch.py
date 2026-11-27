"""Message names a bank/brand but gives a number that is not its published helpline"""
import re
from ...engine import check
from ...data import BRANDS
from ..url.common import _brand_in


@check("official_helpline_mismatch", "Phone", "H", 35, "Message names a bank/brand but gives a number that is not its published helpline", needs="phones")
def helpline_mismatch(ctx):
    b = _brand_in(ctx.text)
    if not b or b not in BRANDS or not BRANDS[b]["phones"]:
        return
    off = BRANDS[b]["phones"]
    digits = [re.sub(r"\D", "", p).lstrip("+") for p in ctx.ids["phones"]]
    wrong = [d for d in digits if not any(d.endswith(o) or o.endswith(d) for o in off)]
    if wrong and len(wrong) == len(digits):
        return f"{b} helplines start {', '.join(off[:2])}…; message gives {wrong[0]}"
