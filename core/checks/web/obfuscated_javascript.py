"""Heavy JavaScript obfuscation (eval, atob, unescape, hex strings)"""
import re
from ...engine import check
from .common import _soup


@check("obfuscated_javascript", "Website", "S", 30, "Heavy JavaScript obfuscation (eval, atob, unescape, hex strings)", needs="html")
def obf_js(ctx):
    js = " ".join(t.get_text() for t in _soup(ctx).find_all("script"))
    n = len(re.findall(r"\beval\s*\(|atob\s*\(|unescape\s*\(|fromCharCode|\\x[0-9a-f]{2}", js, re.I))
    return f"{n} obfuscation markers" if n >= 5 else None
