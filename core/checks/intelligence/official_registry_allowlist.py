"""Info: every link points to a domain in the official registry (RBI banks, government, published brand domains)"""
from ...engine import check
from ..url.common import is_official


@check("official_registry_allowlist", "Intelligence", "L", 0, "Info: every link points to a domain in the official registry (RBI banks, government, published brand domains)", needs="urls")
def official(ctx):
    us = ctx.ids["urls"]
    if us and all(is_official(u["host"]) for u in us):
        return "all links are on published official domains: " + ", ".join(sorted({u["reg"] for u in us})[:4])
