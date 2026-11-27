"""IP address used instead of a domain name"""
import re
from ...engine import check
from .common import _collect, _urls


@check("ip_host", "URL", "S", 30, "IP address used instead of a domain name", needs="urls")
def ip_host(ctx):
    def f(u):
        h = u["host"]
        if re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", h) or re.fullmatch(r"0x[0-9a-f]+|\d{8,10}", h):
            return "IP-address host"
    return _collect(ctx, f)
