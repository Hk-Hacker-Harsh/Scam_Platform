"""Instant meta-refresh or JavaScript redirect to another site"""
import re
from ...engine import check


@check("meta_or_js_redirect", "Website", "S", 20, "Instant meta-refresh or JavaScript redirect to another site", needs="html")
def meta_redirect(ctx):
    m = re.search(r'(?i)<meta[^>]+http-equiv=["\']refresh["\'][^>]+url=([^"\'>\s]+)', ctx.html) or re.search(r"(?i)(?:window\.)?location(?:\.href)?\s*=\s*[\"'](https?://[^\"']+)", ctx.html)
    return f"redirects to {m.group(1)[:60]}" if m else None
