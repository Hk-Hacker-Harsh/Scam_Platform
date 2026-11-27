"""Dynamic-DNS or tunnelling host (ngrok, trycloudflare, duckdns...)"""
from ...engine import check
from ...data import DYNDNS_TUNNEL
from .common import _collect, _urls


@check("dyndns_tunnel_host", "URL", "S", 30, "Dynamic-DNS or tunnelling host (ngrok, trycloudflare, duckdns...)", needs="urls")
def dyndns(ctx):
    return _collect(ctx, lambda u: next((f"host on {d}" for d in DYNDNS_TUNNEL if u["host"] == d or u["host"].endswith("." + d)), None))
