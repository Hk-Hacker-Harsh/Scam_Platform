"""Shares a phone, UPI ID, domain, wallet, bot token or APK with earlier high-risk cases (same campaign)"""
from ...engine import check
from .common import earned_high, linked_cases


@check("identifier_linking_campaigns", "Intelligence", "H", 35, "Shares a phone, UPI ID, domain, wallet, bot token or APK with earlier high-risk cases (same campaign)", needs="any")
def linking(ctx):
    sh = linked_cases(ctx)
    risky = [s for s in sh if s["level"] in ("High", "Confirmed fraud")]
    ok = earned_high(ctx.db, [s["case_id"] for s in risky]) if risky else set()
    bad = [s for s in risky if s["case_id"] in ok]
    if bad:
        s = bad[0]
        return f"shares {s['via'][0][0]} {s['via'][0][1]} with case #{s['case_id']} ({s['level']})" + (f" and {len(bad)-1} other high-risk case(s)" if len(bad) > 1 else "")
