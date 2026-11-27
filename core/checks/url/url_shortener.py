"""Link shortener hides the real destination"""
from ...engine import check
from ...data import SHORTENERS
from .common import _collect, _urls


@check("url_shortener", "URL", "S", 25, "Link shortener hides the real destination", needs="urls")
def shortener(ctx):
    return _collect(ctx, lambda u: "shortener " + u["host"] if u["host"] in SHORTENERS or u["reg"] in SHORTENERS else None)
