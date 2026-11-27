"""Look-alike characters (а→a, 0→o, rn→m) turn the domain into a known brand"""
from ...engine import check
from .common import BRAND_TOKENS, CONFUSABLES, OFFICIAL, _collect, _decode_host, _urls, is_official, skeleton


@check("confusable_brand_match", "URL", "H", 40, "Look-alike characters (а→a, 0→o, rn→m) turn the domain into a known brand", needs="urls")
def confusable_brand_match(ctx):
    def f(u):
        if is_official(u["host"]):
            return
        host = _decode_host(u["host"])
        for label in host.split("."):
            sk = skeleton(label)
            if sk != label.lower():
                for tok, name in BRAND_TOKENS.items():
                    if len(tok) >= 4 and tok in sk and tok not in label.lower():
                        return f"'{label}' reads as '{tok}' ({name}) after normalising look-alike characters"
    return _collect(ctx, f)
