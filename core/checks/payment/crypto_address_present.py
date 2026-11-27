"""Crypto wallet address given for payment"""
from ...engine import check


@check("crypto_address_present", "Payment", "S", 30, "Crypto wallet address given for payment", needs="any")
def crypto(ctx):
    c = ctx.ids.get("crypto")
    return f"{len(c)} wallet address(es), e.g. {c[0][:14]}…" if c else None
