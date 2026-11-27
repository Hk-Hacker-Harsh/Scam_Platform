"""URL contains user@host so the visible part is not the real host"""
from ...engine import check
from .common import _collect, _urls


@check("userinfo_at_trick", "URL", "H", 40, "URL contains user@host so the visible part is not the real host", needs="urls")
def userinfo_at(ctx):
    return _collect(ctx, lambda u: f"'{u['userinfo']}@' prefix hides the real host {u['host']}" if u["userinfo"] else None)
