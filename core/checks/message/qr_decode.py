"""QR code in a screenshot (quishing). The decoded link / UPI ID is also passed to the URL and payment checks,
because the payload is added to the analysed text."""
import re

from ...engine import check
from ...image_input import parse_upi_qr

RECEIVE_LURE = re.compile(r"(?i)(receive|refund|cashback|prize|reward|won|winner|lottery|credited|get money|paisa milega|"
                          r"इनाम|रिफंड|जीत|पैसे मिलेंगे|कैशबैक)")


@check("qr_decode", "Message", "S", 12,
       "Screenshot contains a QR code that opens a link or a UPI payment (quishing). Scanning a QR can only PAY money, never receive it",
       needs="qr")
def qr_decode(ctx):
    out = []
    for p in ctx.qr:
        u = parse_upi_qr(p)
        if u:
            if u["action"] == "collect":
                out.append(f"UPI collect request from {u['pa'] or 'unknown'}: it pulls money from you")
            else:
                out.append(f"UPI payment QR to {u['pa'] or 'unknown'}" + (f" for ₹{u['am']}" if u["am"] else ""))
        elif re.match(r"(?i)^(https?://|www\.)", p):
            out.append(f"QR opens link {p[:80]}")
    return out or None

