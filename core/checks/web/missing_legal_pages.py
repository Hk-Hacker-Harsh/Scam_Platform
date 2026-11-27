"""No privacy policy, terms or about page links"""
import re
from ...engine import check
from .common import _soup


@check("missing_legal_pages", "Website", "S", 15, "No privacy policy, terms or about page links", needs="html")
def no_legal(ctx):
    links = " ".join((a.get("href") or "") + " " + a.get_text(" ", strip=True) for a in _soup(ctx).find_all("a")).lower()
    if _soup(ctx).find_all("form") and not re.search(r"privacy|terms|about us|t&c|disclaimer", links):
        return "has a form but no privacy / terms / about links"
