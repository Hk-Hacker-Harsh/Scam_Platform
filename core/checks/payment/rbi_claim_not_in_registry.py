"""Claims RBI/NBFC approval but no matching entity is in the RBI registry"""
import re
from ...engine import check
from ...data import rbi_entities


@check("rbi_claim_not_in_registry", "Payment", "H", 35, "Claims RBI/NBFC approval but no matching entity is in the RBI registry", needs="text")
def rbi_claim(ctx):
    blob = ctx.text + " " + ctx.html
    if not re.search(r"(?i)\b(rbi|reserve bank)\b.{0,30}(approved|registered|licen[cs]ed|regulated)|nbfc (registered|approved)", blob):
        return
    m = re.search(r"(?i)([A-Z][A-Za-z&. ]{3,50}(?:Finance|Finserv|Capital|Credit|Loans?|Fincorp|Financial)[A-Za-z. ]{0,25}(?:Limited|Ltd\.?|Pvt\.? Ltd\.?|Private Limited))", blob)
    if not m:
        return "claims RBI approval without naming a registered entity"
    name = re.sub(r"\W+", " ", m.group(1).lower()).strip()
    ents = {re.sub(r"\W+", " ", e.lower()).strip() for e in rbi_entities()}
    if name not in ents and not any(name in e for e in ents):
        return f"claims RBI approval; '{m.group(1).strip()}' not found in RBI registry"
