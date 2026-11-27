"""Sender/brand-lookalike domain publishes no SPF or DMARC"""
from ...engine import check
from ..url.common import OFFICIAL, _urls, is_official


@check("domain_no_email_auth", "Domain", "S", 10, "Sender/brand-lookalike domain publishes no SPF or DMARC", needs="urls", net=True)
def no_email_auth(ctx):
    from ...netcache import dns_txt
    out = []
    for dom in {u["reg"] for u in _urls(ctx) if not is_official(u["host"])}:
        try:
            txt = dns_txt(dom)
        except Exception:
            continue
        if "v=spf1" not in txt.lower():
            out.append(f"{dom} has no SPF record")
    return out
