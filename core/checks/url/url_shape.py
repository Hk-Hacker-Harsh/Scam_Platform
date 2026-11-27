"""Very long URL, many subdomains, hyphens or digits"""
from ...engine import check
from .common import _collect, _urls


@check("url_shape", "URL", "S", 20, "Very long URL, many subdomains, hyphens or digits", needs="urls")
def url_shape(ctx):
    def f(u):
        why = []
        if len(u["raw"]) > 110:
            why.append(f"{len(u['raw'])} characters")
        if u["host"].count(".") >= 4:
            why.append("many subdomains")
        if u["reg"].count("-") >= 3:
            why.append("many hyphens")
        if sum(c.isdigit() for c in u["reg"]) >= 5:
            why.append("many digits in domain")
        return ", ".join(why) or None
    return _collect(ctx, f)
