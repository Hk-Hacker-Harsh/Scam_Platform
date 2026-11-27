"""Domain registered in the last 30 days (RDAP)"""
from ...engine import check
from ..url.common import OFFICIAL, _rdap_created, _urls, is_official


@check("domain_age_young", "Domain", "S", 35, "Domain registered in the last 30 days (RDAP)", needs="urls", net=True)
def domain_age(ctx):
    from datetime import datetime, timezone
    out = []
    for dom in {u["reg"] for u in _urls(ctx) if not is_official(u["host"])}:
        try:
            created = _rdap_created(dom)
        except Exception:
            continue
        if created:
            days = (datetime.now(timezone.utc) - created).days
            if days <= 30:
                out.append(f"{dom} registered {days} day(s) ago")
    return out
