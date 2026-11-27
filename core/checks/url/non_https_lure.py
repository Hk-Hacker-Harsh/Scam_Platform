"""Plain http (no TLS) on a page that looks like a login/KYC/payment lure"""
from ...engine import check
from ...data import RISKY_PATH_WORDS
from .common import OFFICIAL, _collect, _urls, is_official


@check("non_https_lure", "URL", "S", 15, "Plain http (no TLS) on a page that looks like a login/KYC/payment lure", needs="urls")
def non_https(ctx):
    return _collect(ctx, lambda u: "http:// with lure words" if u["scheme"] == "http" and u["had_scheme"] and any(w in (u["host"] + u["path"]).lower() for w in RISKY_PATH_WORDS) and not is_official(u["host"]) else None)
