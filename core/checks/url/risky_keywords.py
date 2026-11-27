"""Words like login, verify, kyc, claim, refund in host/path of a non-official domain"""
from ...engine import check
from ...data import RISKY_PATH_WORDS
from .common import OFFICIAL, _collect, _urls, is_official
from urllib.parse import unquote


@check("risky_keywords", "URL", "S", 20, "Words like login, verify, kyc, claim, refund in host/path of a non-official domain", needs="urls")
def risky_kw(ctx):
    def f(u):
        if is_official(u["host"]):
            return
        t = (u["host"] + unquote(u["path"])).lower()
        hit = [w for w in RISKY_PATH_WORDS if w in t]
        return "contains " + ", ".join(hit[:4]) if hit else None
    return _collect(ctx, f)
