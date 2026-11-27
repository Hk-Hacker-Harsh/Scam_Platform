"""Query parameter carries another URL (redirect/url/next=...) - open-redirect abuse"""
import re
from ...engine import check
from .common import _collect, _urls
from urllib.parse import parse_qsl, unquote


@check("open_redirect_param", "URL", "S", 30, "Query parameter carries another URL (redirect/url/next=...) - open-redirect abuse", needs="urls")
def open_redirect(ctx):
    def f(u):
        for k, v in parse_qsl(u["query"], keep_blank_values=True):
            v = unquote(v)
            if k.lower() in {"url", "redirect", "redirect_uri", "next", "return", "returnurl", "goto", "target", "dest", "continue", "link", "u"} and re.match(r"(?i)(https?:)?//", v):
                return f"parameter '{k}' redirects to {v[:60]}"
        if re.search(r"(?i)(//|%2f%2f)[^/]+\.[a-z]{2,}.*(//|%2f%2f)", u["path"] + "?" + u["query"]):
            return "second URL embedded in the path"
    return _collect(ctx, f)
