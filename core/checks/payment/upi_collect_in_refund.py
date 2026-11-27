"""Asks you to pay/collect via UPI while promising a refund/prize/loan"""
from ...engine import check
from .common import _hits


@check("upi_collect_in_refund", "Payment", "H", 35, "Asks you to pay/collect via UPI while promising a refund/prize/loan", needs="upis")
def upi_in_lure(ctx):
    if ctx.kind in ("message", "email") and (_hits(ctx, "prize") or _hits(ctx, "refund_collect") or _hits(ctx, "loan")):
        return f"UPI ID {ctx.ids['upis'][0]} given in a refund/prize/loan context"
