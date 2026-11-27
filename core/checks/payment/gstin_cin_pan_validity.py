"""GSTIN / PAN / CIN shown on the page or message fails its format or checksum"""
from ...engine import check
from ...extract import gstin_ok


@check("gstin_cin_pan_validity", "Payment", "S", 25, "GSTIN / PAN / CIN shown on the page or message fails its format or checksum", needs="any")
def gst(ctx):
    out = []
    for g in ctx.ids.get("gstin", []):
        if not gstin_ok(g):
            out.append(f"GSTIN {g} fails checksum")
    return out
