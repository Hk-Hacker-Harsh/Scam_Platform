"""Domain label is 1-2 edits from a known brand domain (typosquat)"""
from ...engine import check
from .common import BRAND_TOKENS, OFFICIAL, _collect, _decode_host, _urls, is_official, lev


@check("edit_distance_typosquat", "URL", "S", 35, "Domain label is 1-2 edits from a known brand domain (typosquat)", needs="urls")
def typosquat(ctx):
    def f(u):
        if is_official(u["host"]):
            return
        label = _decode_host(u["reg"]).split(".")[0]
        for tok, name in BRAND_TOKENS.items():
            if len(tok) >= 5 and label != tok and 0 < lev(label, tok) <= (1 if len(tok) < 8 else 2) and abs(len(label) - len(tok)) <= 2:
                return f"'{label}' is {lev(label, tok)} edit(s) from '{tok}' ({name})"
    return _collect(ctx, f)
