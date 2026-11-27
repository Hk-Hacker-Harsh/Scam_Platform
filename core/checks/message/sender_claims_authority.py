"""Claims to be a bank/government body but the message links to or names an unrelated domain"""
from ...engine import check
from ..url.common import _brand_in, is_official


@check("sender_claims_authority", "Message", "S", 20, "Claims to be a bank/government body but the message links to or names an unrelated domain", needs="urls")
def claims_authority(ctx):
    if ctx.kind not in ("message", "email") or "addr_only" in ctx.notes:
        return
    b = _brand_in(ctx.text)
    bad = [u["host"] for u in ctx.ids["urls"] if not is_official(u["host"])]
    if b and bad:
        return f"mentions {b} but links to {bad[0]}"
