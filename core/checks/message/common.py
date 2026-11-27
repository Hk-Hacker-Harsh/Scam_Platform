"""Helpers shared by the message checks. Keyword patterns live in core/data.py (KW)."""
import re

from ...data import KW
from ...engine import check
from ...extract import ZW_RE


def _kw(ctx, key, flags=re.I | re.S):
    hits = []
    t = ZW_RE.sub("", ctx.text)
    for p in KW[key]:
        m = re.search(p, t, flags)
        if m:
            hits.append(m.group(0)[:50].strip())
    return hits


def lexicon_check(cid, key, tier, weight, desc, label):
    """Register a check that fires when any pattern in KW[key] matches the message text."""
    def fn(ctx):
        h = _kw(ctx, key)
        return f"{label}: “{h[0]}”" + (f" (+{len(h)-1} more)" if len(h) > 1 else "") if h else None
    fn.__name__ = cid
    check(cid, "Message", tier, weight, desc, needs="text")(fn)
