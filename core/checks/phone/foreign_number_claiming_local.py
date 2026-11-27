"""Foreign (+92, +880, +1...) number in a message that claims to be an Indian bank/government/courier"""
import re
from ...engine import check
from ...data import FOREIGN_CC
from ..url.common import _brand_in


@check("foreign_number_claiming_local", "Phone", "H", 35, "Foreign (+92, +880, +1...) number in a message that claims to be an Indian bank/government/courier", needs="phones")
def foreign_number(ctx):
    b = _brand_in(ctx.text)
    f = [p for p in ctx.ids["phones"] if any(p.startswith(c) for c in FOREIGN_CC)]
    if f and (b or re.search(r"(?i)\b(rbi|bank|police|customs|kyc|aadhaar|income tax)\b", ctx.text)):
        return f"{f[0]} used while message sounds Indian official" + (f" ({b})" if b else "")
