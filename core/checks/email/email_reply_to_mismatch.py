"""Reply-To or Return-Path domain differs from the From domain"""
from ...engine import check
from ...extract import registered_domain
from .common import _from_dom, _hdr
from email.utils import parseaddr


@check("email_reply_to_mismatch", "Email", "S", 30, "Reply-To or Return-Path domain differs from the From domain", needs="headers")
def reply_mismatch(ctx):
    f = _from_dom(ctx)
    for h in ("Reply-To", "Return-Path"):
        a = parseaddr(_hdr(ctx, h))[1]
        if a and registered_domain(a.split("@")[-1].lower()) != f:
            return f"{h} {a} vs From domain {f}"
