"""Helpers shared by the email checks."""
from ...extract import registered_domain
from email.utils import parseaddr


def _hdr(ctx, k):
    return (ctx.headers.get(k) or "") if ctx.headers is not None else ""


def _from_dom(ctx):
    return registered_domain(parseaddr(_hdr(ctx, "From"))[1].split("@")[-1].lower())
