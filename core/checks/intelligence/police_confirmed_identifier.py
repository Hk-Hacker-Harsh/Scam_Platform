"""An identifier in this input was marked 'confirmed fraud' by the police team"""
from ...engine import check


@check("police_confirmed_identifier", "Intelligence", "H", 100, "An identifier in this input was marked 'confirmed fraud' by the police team", needs="any")
def police_confirmed(ctx):
    if not ctx.db:
        return
    hits = [l for l in ctx.db.labels_for(ctx.pairs) if l["label"] == "confirmed_fraud"]
    return [f"{l['type']} {l['value']} confirmed fraud on {l['ts'][:10]}" for l in hits][:3]
