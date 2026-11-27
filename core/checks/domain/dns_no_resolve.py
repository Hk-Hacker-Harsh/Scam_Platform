"""Domain does not resolve (A/AAAA) - dead or takedown-evading"""
import re
from ...engine import check
from ..url.common import _urls


@check("dns_no_resolve", "Domain", "S", 20, "Domain does not resolve (A/AAAA) - dead or takedown-evading", needs="urls", net=True)
def dns_no(ctx):
    from ...netcache import dns_status
    out = []
    for dom in {u["host"] for u in _urls(ctx) if not re.fullmatch(r"[\d.]+", u["host"])}:
        try:
            if dns_status(dom, "A") == "nxdomain":
                out.append(f"{dom} does not exist in DNS")
        except Exception:   # timeout / offline without a cached answer: no verdict either way
            pass
    return out
