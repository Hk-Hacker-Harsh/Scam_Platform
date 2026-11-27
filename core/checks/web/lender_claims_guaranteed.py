"""Lender page promises guaranteed approval, no documents or upfront fee"""
import re
from ...engine import check
from .common import _soup


@check("lender_claims_guaranteed", "Website", "H", 35, "Lender page promises guaranteed approval, no documents or upfront fee", needs="html")
def lender_claims(ctx):
    t = _soup(ctx).get_text(" ", strip=True)
    pats = [r"guaranteed (loan )?(approval|disbursal)", r"100% (approval|guaranteed)", r"no (cibil|credit score|documents?) (required|needed|check)",
            r"(processing|registration|insurance|advance) fee .{0,30}(upfront|before|in advance)", r"loan (in|within) \d+ ?(min|minutes|seconds)"]
    hit = [p for p in pats if re.search(p, t, re.I)]
    return f"{len(hit)} lender red-flag claim(s): “{re.search(hit[0], t, re.I).group(0)[:50]}”" if hit else None
