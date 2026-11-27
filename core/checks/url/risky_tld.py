"""Top-level domain heavily used for throw-away scam sites"""
from ...engine import check
from ...data import RISKY_TLDS
from .common import OFFICIAL, _collect, _urls, is_official


@check("risky_tld", "URL", "S", 15, "Top-level domain heavily used for throw-away scam sites", needs="urls")
def risky_tld(ctx):
    return _collect(ctx, lambda u: f".{u['host'].rsplit('.', 1)[-1]} TLD" if u["host"].rsplit(".", 1)[-1] in RISKY_TLDS and not is_official(u["host"]) else None)
