"""Helpers shared by the payment checks."""
from ...data import KW
import re


def _hits(ctx, key):
    return any(re.search(p, ctx.text, re.I | re.S) for p in KW[key])
