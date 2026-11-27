"""A UPI QR shown as a way to RECEIVE money (refund, prize). Scanning a QR can only pay money out."""
from ...engine import check
from ...image_input import parse_upi_qr
from .qr_decode import RECEIVE_LURE


@check("qr_receive_money_trick", "Message", "H", 40,
       "A UPI payment / collect QR is presented as a way to receive a refund, prize or money. Scanning a QR never receives money",
       needs="qr")
def qr_receive_money_trick(ctx):
    if not RECEIVE_LURE.search(ctx.text):
        return None
    for p in ctx.qr:
        u = parse_upi_qr(p)
        if u:
            return f"UPI {u['action']} QR to {u['pa'] or 'unknown'} with receive-money wording"
    return None
