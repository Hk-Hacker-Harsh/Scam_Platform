"""Talks to raw IP addresses or over plain http (cleartext) to non-official servers"""
import re
from ...engine import check
from ..url.common import is_official


@check("apk_cleartext_ip_endpoints", "APK", "S", 20, "Sends data to raw IP addresses or over plain http (cleartext traffic allowed)", needs="apk")
def cleartext(ctx):
    out = []
    ips = [u["host"] for u in ctx.ids.get("urls", []) if re.fullmatch(r"[\d.]+", u["host"])]
    if ips:
        out.append("IP endpoints: " + ", ".join(sorted(set(ips))[:3]))
    plain = sorted({u["host"] for u in ctx.ids.get("urls", []) if u["scheme"] == "http" and u.get("had_scheme")
                    and not is_official(u["host"]) and u["host"] not in ips})
    if plain and ctx.apk.get("cleartext") is not False:
        out.append("plain-http servers: " + ", ".join(plain[:3]))
    if ctx.apk.get("cleartext") and out:
        out.append("manifest allows cleartext traffic")
    return out or None
