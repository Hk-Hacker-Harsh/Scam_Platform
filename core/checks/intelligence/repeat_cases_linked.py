"""Shares identifiers with two or more earlier cases (any level)"""
from ...engine import check
from .common import linked_cases


@check("repeat_cases_linked", "Intelligence", "S", 20, "Shares identifiers with two or more earlier cases (not counting re-scans of the same site or app)", needs="any")
def repeat_linked(ctx):
    sh = linked_cases(ctx)
    if len(sh) >= 2 and not any(s["level"] in ("High", "Confirmed fraud") for s in sh):
        return f"linked to {len(sh)} earlier case(s) via {sh[0]['via'][0][0]} {sh[0]['via'][0][1]}"
