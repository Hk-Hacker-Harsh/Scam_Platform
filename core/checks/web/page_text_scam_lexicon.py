"""Page text uses the same scam lexicon as messages (KYC pretext, prize, OTP, urgency)"""
import re
from ...engine import check
from .common import _soup


@check("page_text_scam_lexicon", "Website", "S", 25, "Page text uses the same scam lexicon as messages (KYC pretext, prize, OTP, urgency)", needs="html")
def page_lexicon(ctx):
    from ...data import KW
    t = _soup(ctx).get_text(" ", strip=True)
    hit = [k for k in ("otp_pin", "kyc", "prize", "urgency", "investment", "task_job") if any(re.search(p, t, re.I) for p in KW[k])]
    return "page text matches: " + ", ".join(hit) if len(hit) >= 2 else None
