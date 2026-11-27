"""javascript:, data: or file: URI used as a link"""
import re
from ...engine import check


@check("dangerous_uri_scheme", "URL", "H", 35, "javascript:, data: or file: URI used as a link", needs="text")
def uri_scheme(ctx):
    m = re.search(r"(?i)\b(javascript|vbscript|file):[^\s]{3,}|data:text/html[^\s]*", ctx.text)
    return f"found {m.group(0)[:40]}" if m else None
