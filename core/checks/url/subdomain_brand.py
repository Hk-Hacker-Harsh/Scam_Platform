"""Brand shown as a subdomain while the real (registered) domain is unrelated"""
from ...engine import check
from .common import BRAND_TOKENS, OFFICIAL, _brand_in, _collect, _urls, is_official


@check("subdomain_brand", "URL", "H", 35, "Brand shown as a subdomain while the real (registered) domain is unrelated", needs="urls")
def subdomain_brand(ctx):
    def f(u):
        if is_official(u["host"]) or u["host"] == u["reg"]:
            return
        sub = u["host"][: -len(u["reg"])].rstrip(".")
        b = _brand_in(sub)
        if b and not _brand_in(u["reg"].rsplit(".", 1)[0]):
            return f"'{sub}' pretends to be {b}; real domain is {u['reg']}"
    return _collect(ctx, f)
