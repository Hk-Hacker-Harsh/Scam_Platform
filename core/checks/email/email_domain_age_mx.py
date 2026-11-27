"""Sender domain has no MX record (cannot receive replies) - spoofed"""
from ...engine import check
from .common import _hdr
from email.utils import parseaddr


@check("email_domain_age_mx", "Email", "S", 20, "Sender domain has no MX record (cannot receive replies) - spoofed", needs="headers", net=True)
def no_mx(ctx):
    from ...netcache import dns_status
    dom = parseaddr(_hdr(ctx, "From"))[1].split("@")[-1].lower()
    try:
        st = dns_status(dom, "MX")
    except Exception:
        return None
    if st == "nxdomain":
        return f"{dom} does not exist"
    if st == "noanswer":
        return f"{dom} has no MX record"
    return None
