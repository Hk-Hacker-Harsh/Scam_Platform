"""URL carries a script/XSS payload (<script>, onerror=, javascript:)"""
import re
from ...engine import check
from urllib.parse import unquote


@check("xss_payload_in_url", "URL", "H", 40, "URL carries a script/XSS payload (<script>, onerror=, javascript:)", needs="text")
def xss(ctx):
    t = unquote(unquote(ctx.text)).lower()
    pats = [r"<\s*script", r"javascript\s*:", r"on(error|load|click|mouseover|focus)\s*=", r"<\s*(img|svg|iframe)[^>]*(src|onload)", r"document\.cookie", r"alert\s*\(", r"data:text/html", r"vbscript:"]
    hit = [p for p in pats if re.search(p, t)]
    return f"matched {len(hit)} script-injection pattern(s)" if hit else None
