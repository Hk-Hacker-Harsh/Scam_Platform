"""No SPF/DKIM/DMARC results found in headers"""
from ...engine import check
from .common import _hdr


@check("email_auth_headers_missing", "Email", "S", 15, "No SPF/DKIM/DMARC results found in headers", needs="headers")
def auth_missing(ctx):
    if "addr_only" in ctx.notes:
        return
    ar = (_hdr(ctx, "Authentication-Results") + _hdr(ctx, "Received-SPF") + _hdr(ctx, "DKIM-Signature")).lower()
    if not any(k in ar for k in ("spf", "dkim", "dmarc")):
        return "headers carry no authentication results (forwarded copy or injected mail)"
