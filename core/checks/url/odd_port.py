"""Non-standard port in the URL"""
from ...engine import check
from .common import _collect, _urls


@check("odd_port", "URL", "S", 15, "Non-standard port in the URL", needs="urls")
def odd_port(ctx):
    return _collect(ctx, lambda u: f"port {u['port']}" if u["port"] and u["port"] not in (80, 443) else None)
