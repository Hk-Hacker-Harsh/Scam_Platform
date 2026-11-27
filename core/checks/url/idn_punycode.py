"""Hostname uses punycode (xn--) or non-ASCII letters (homograph attack)"""
from ...engine import check
from ...extract import has_non_ascii_letters
from .common import _collect, _decode_host, _urls


@check("idn_punycode", "URL", "H", 35, "Hostname uses punycode (xn--) or non-ASCII letters (homograph attack)", needs="urls")
def idn_punycode(ctx):
    return _collect(ctx, lambda u: ("punycode " + u["host"] + " displays as " + _decode_host(u["host"]))
                    if any(l.startswith("xn--") for l in u["host"].split(".")) else ("non-ASCII letters in hostname" if has_non_ascii_letters(u["host"]) else None))
