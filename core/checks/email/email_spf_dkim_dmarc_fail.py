"""Receiving server recorded SPF, DKIM or DMARC failure"""
import re
from ...engine import check
from .common import _hdr


@check("email_spf_dkim_dmarc_fail", "Email", "H", 40, "Receiving server recorded SPF, DKIM or DMARC failure", needs="headers")
def auth_fail(ctx):
    ar = (_hdr(ctx, "Authentication-Results") + " " + _hdr(ctx, "Received-SPF")).lower()
    bad = [k for k in ("spf", "dkim", "dmarc") if re.search(rf"{k}\s*=\s*(fail|softfail|permerror)", ar) or (k == "spf" and ar.strip().startswith(("fail", "softfail")))]
    return "failed: " + ", ".join(bad) if bad else None
