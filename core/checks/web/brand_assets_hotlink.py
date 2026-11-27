"""Page loads logos/images straight from a brand's site while being a different domain"""
from ...engine import check
from ..url.common import is_official
from .common import _page_host, _soup
from urllib.parse import urlsplit


@check("brand_assets_hotlink", "Website", "H", 30, "Page loads logos/images straight from a brand's site while being a different domain", needs="html")
def hotlink(ctx):
    s = _soup(ctx)
    host = _page_host(ctx)
    for tag in s.find_all(["img", "link", "script"]):
        src = tag.get("src") or tag.get("href") or ""
        if src.startswith(("http", "//")):
            h = urlsplit(src if src.startswith("http") else "http:" + src).hostname or ""
            if h and is_official(h) and (not host or not is_official(host)) and tag.name == "img":
                return f"image hot-linked from {h} on page hosted at {host or 'unknown'}"
