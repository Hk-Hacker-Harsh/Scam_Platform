"""Sender domain is a look-alike of a known brand"""
from ...engine import check
from ...extract import registered_domain
from ..url.common import is_official, lev
from .common import _hdr
from email.utils import parseaddr


@check("email_lookalike_sender_domain", "Email", "H", 40, "Sender domain is a look-alike of a known brand", needs="headers")
def lookalike_sender(ctx):
    dom = parseaddr(_hdr(ctx, "From"))[1].split("@")[-1].lower()
    if not dom or is_official(dom):
        return
    from ..url.common import skeleton, BRAND_TOKENS
    label = registered_domain(dom).split(".")[0]
    for tok in BRAND_TOKENS:
        if len(tok) >= 5 and label != tok and (lev(skeleton(label), tok) <= 1):
            return f"{dom} resembles {tok}"
