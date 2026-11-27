"""Brand name combined with a lure word (hdfc-kyc-update, sbi-refund) on an unrelated domain"""
import re
from ...engine import check
from ...data import LURE_WORDS
from .common import BRAND_TOKENS, OFFICIAL, _brand_in, _collect, _decode_host, _urls, is_official


@check("combosquat", "URL", "S", 40, "Brand name combined with a lure word (hdfc-kyc-update, sbi-refund) on an unrelated domain", needs="urls")
def combosquat(ctx):
    def f(u):
        if is_official(u["host"]):
            return
        regl = _decode_host(u["reg"]).rsplit(".", 1)[0].replace(".", "-")
        parts = [p for p in re.split(r"[-_.]", regl) if p]
        brand = _brand_in(regl)
        lure = [w for w in LURE_WORDS if w in parts or any(p.startswith(w) for p in parts)]
        if brand and lure:
            return f"brand '{brand}' + lure word '{lure[0]}'"
    return _collect(ctx, f)
