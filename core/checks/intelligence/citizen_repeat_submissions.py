"""Same text/URL/APK has already been submitted several times"""
from ...engine import check


@check("citizen_repeat_submissions", "Intelligence", "S", 10, "Same text/URL/APK has already been submitted several times", needs="any")
def repeats(ctx):
    # counts every submission of the same input, including repeats answered from the result cache
    if not ctx.db or not getattr(ctx, "ckey", None):
        return
    n = ctx.db.times_submitted(ctx.ckey)
    return f"submitted {n} time(s) before" if n >= 3 else None
