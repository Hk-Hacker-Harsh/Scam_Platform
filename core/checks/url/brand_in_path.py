"""Brand name only in the path of an unrelated domain"""
from ...engine import check
from .common import BRAND_TOKENS, OFFICIAL, _brand_in, _collect, _urls, is_official
from urllib.parse import unquote


@check("brand_in_path", "URL", "S", 25, "Brand name only in the path of an unrelated domain", needs="urls")
def brand_in_path(ctx):
    def f(u):
        if is_official(u["host"]):
            return
        b = _brand_in(unquote(u["path"]))
        if b and not _brand_in(u["host"]):
            return f"path mentions {b} but domain is {u['reg']}"
    return _collect(ctx, f)
