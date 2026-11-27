"""Servers the app talks to look malicious (IP hosts, tunnels, look-alike domains, shorteners)"""
import re
from ...engine import check
from ..url.common import is_official


@check("apk_embedded_endpoint_reputation", "APK", "H", 35, "Servers the app talks to look malicious (IP hosts, tunnels, look-alike domains, shorteners)", needs="apk")
def endpoints(ctx):
    from ...engine import REGISTRY
    urls = [u for u in ctx.ids.get("urls", []) if not is_official(u["host"]) and not re.search(r"(?i)(schemas\.android|w3\.org|apache\.org|google|gstatic|googleapis|facebook|firebase|crashlytics|github\.com|android\.com|xmlpull|mozilla|jquery|example\.)", u["host"])]
    if not urls:
        return
    class Sub:  # minimal context so URL checks can be reused unchanged
        pass
    from ...engine import Ctx
    sub = Ctx(kind="url", text=" ".join(u["raw"] for u in urls), ids={"urls": urls, "domains": [u["reg"] for u in urls]})
    out = []
    for cid in ("ip_host", "dyndns_tunnel_host", "confusable_brand_match", "edit_distance_typosquat", "combosquat", "url_shortener",
                "free_hosting_abuse", "idn_punycode", "risky_tld", "subdomain_brand"):
        r = REGISTRY[cid]["fn"](sub)
        if r:
            out.append(f"{cid}: {r[0] if isinstance(r, list) else r}")
    return out[:3]
