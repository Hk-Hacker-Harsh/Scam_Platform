"""Page title/heading claims to be a known brand but the domain is not that brand's"""
from ...engine import check
from ..url.common import _brand_in, is_official
from .common import _page_host, _soup


@check("title_brand_mismatch", "Website", "S", 30, "Page title/heading claims to be a known brand but the domain is not that brand's", needs="html")
def title_brand(ctx):
    s = _soup(ctx)
    host = _page_host(ctx)
    t = (s.title.string if s.title and s.title.string else "") + " " + " ".join(h.get_text(" ", strip=True) for h in s.find_all(["h1", "h2"])[:3])
    b = _brand_in(t)
    if b and host and not is_official(host) and not _brand_in(host):
        return f"page says '{b}' but domain is {host}"
