"""Helpers shared by the url checks."""
from ...data import BRANDS
from ...data import DYNDNS_TUNNEL
from ...data import FREE_HOSTS
from ...data import GOV_TLD_SUFFIXES
from ...data import LURE_WORDS
from ...data import RISKY_PATH_WORDS
from ...data import RISKY_TLDS
from ...data import SHORTENERS
from ...data import official_domains
from ...engine import check
from ...extract import ZW_RE
from ...extract import has_non_ascii_letters
from ...extract import registered_domain
from ...extract import scripts_in
from urllib.parse import parse_qsl
from urllib.parse import unquote
import math
import re
import unicodedata


CONFUSABLES = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "i", "ј": "j", "ѕ": "s", "һ": "h", "ԁ": "d",
    "ɡ": "g", "ӏ": "l", "ο": "o", "ν": "v", "α": "a", "ρ": "p", "τ": "t", "ι": "i", "κ": "k", "ɑ": "a", "ǝ": "e", "ո": "n",
    "ᴀ": "a", "ᴅ": "d", "ⅼ": "l", "ⅰ": "i", "0": "o", "1": "l", "5": "s", "3": "e",
}


BRAND_TOKENS = {}


for _name, _b in BRANDS.items():
    _tok = _name.replace(" ", "")
    BRAND_TOKENS[_tok] = _name
    for _d in _b["domains"]:
        _l = _d.split(".")[0]
        if len(_l) >= 4 and _l not in ("pay", "gpay"):
            BRAND_TOKENS.setdefault(_l, _name)


BRAND_TOKENS.pop("income", None)


BRAND_TOKENS["incometax"] = "income tax"


OFFICIAL = official_domains()


def is_official(host: str) -> bool:
    host = host.lower()
    if host.endswith(GOV_TLD_SUFFIXES):
        return True
    return any(host == d or host.endswith("." + d) for d in OFFICIAL)


def skeleton(label: str) -> str:
    s = unicodedata.normalize("NFKD", label.lower())
    s = "".join(CONFUSABLES.get(c, c) for c in s if not unicodedata.combining(c))
    return s.replace("rn", "m").replace("vv", "w")


def _ascii_label(label):
    return label.encode("ascii", "ignore").decode() == label


def lev(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _decode_host(host: str) -> str:
    try:
        return ".".join(l.encode("ascii").decode("idna") if l.startswith("xn--") else l for l in host.split("."))
    except Exception:
        return host


def _brand_in(text: str):
    t = text.lower()
    for tok, name in BRAND_TOKENS.items():
        if re.search(r"(?<![a-z0-9])" + re.escape(tok) + r"(?![a-z0-9])", t) or (len(tok) >= 5 and tok in t):
            return name
    return None


def _urls(ctx):
    return [u for u in ctx.ids.get("urls", []) if u["host"]]


def _collect(ctx, fn):
    out = []
    for u in _urls(ctx):
        r = fn(u)
        if r:
            out.append(f"{u['host']}: {r}")
    return out


def _rdap_created(domain):
    """Registration date (UTC datetime) or None. Answers are cached in instance/netcache.db (see core/netcache.py)."""
    from datetime import datetime, timezone
    from ... import netcache
    key = f"rdap:{domain.lower()}"
    hit, val = netcache.get(key, netcache.TTL["rdap"])
    if hit and val is None and not netcache.cache_only():
        hit, val = netcache.get(key, netcache.TTL["rdap_none"])   # re-ask sooner when the registry had no date

    def look():
        import requests
        r = requests.get(f"https://rdap.org/domain/{domain}", timeout=6, headers={"Accept": "application/rdap+json"})
        if r.status_code == 404:
            return None
        r.raise_for_status()          # rate limits / server errors are not cached
        for ev in r.json().get("events", []):
            if ev.get("eventAction") == "registration":
                return ev["eventDate"]
        return None
    if not hit:
        val = netcache.cached(key, 0, look)
    if not val:
        return None
    return datetime.fromisoformat(val.replace("Z", "+00:00")).astimezone(timezone.utc)
