"""Unverifiable trust badges: 'RBI approved', 'SEBI registered', 'ISO certified' with no registration number"""
import re
from ...engine import check
from .common import _soup


@check("fake_trust_claims", "Website", "S", 20, "Unverifiable trust badges: 'RBI approved', 'SEBI registered', 'ISO certified' with no registration number", needs="html")
def trust_claims(ctx):
    t = _soup(ctx).get_text(" ", strip=True)
    if re.search(r"(?i)(rbi|sebi|irdai|iso|government) (approved|registered|certified|authorised)", t) and not re.search(r"(?i)(reg(istration)?\.? ?(no|number)|licen[cs]e ?(no|number)|CIN|NBFC.?[A-Z0-9-]{5,})", t):
        return "trust badge claimed with no registration/licence number"
