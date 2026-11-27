"""Brand or lure page hosted on a free hosting / page-builder service"""
from ...engine import check
from ...data import FREE_HOSTS, RISKY_PATH_WORDS
from .common import BRAND_TOKENS, _brand_in, _collect, _urls


@check("free_hosting_abuse", "URL", "S", 25, "Brand or lure page hosted on a free hosting / page-builder service", needs="urls")
def free_hosting(ctx):
    def f(u):
        for fh in FREE_HOSTS:
            if u["host"] == fh or u["host"].endswith("." + fh):
                if _brand_in(u["host"] + u["path"]) or any(w in (u["host"] + u["path"]).lower() for w in RISKY_PATH_WORDS):
                    return f"brand/lure page on free host {fh}"
    return _collect(ctx, f)
