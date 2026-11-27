"""Page asks for password / OTP / card / Aadhaar / PAN / PIN in a form on a non-official domain"""
import re
from ...engine import check
from ...data import SENSITIVE_FIELD_WORDS
from ..url.common import is_official
from .common import _page_host, _soup


@check("sensitive_fields_form", "Website", "H", 35, "Page asks for password / OTP / card / Aadhaar / PAN / PIN in a form on a non-official domain", needs="html")
def sensitive_fields(ctx):
    host = _page_host(ctx)
    if host and is_official(host):
        return
    s = _soup(ctx)
    hits = set()
    for inp in s.find_all("input"):
        blob = " ".join(str(inp.get(a, "")) for a in ("name", "id", "placeholder", "type", "aria-label")).lower()
        if inp.get("type") == "password":
            hits.add("password")
        for w in SENSITIVE_FIELD_WORDS:
            if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", blob):
                hits.add(w)
    return f"form collects: {', '.join(sorted(hits)[:6])}" if len(hits) >= 1 and (len(hits) >= 2 or "password" in hits or "otp" in hits or "cvv" in hits) else None
