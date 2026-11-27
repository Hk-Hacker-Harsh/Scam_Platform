"""Domain name looks machine-generated (high entropy, few vowels)"""
import math
from ...engine import check
from .common import OFFICIAL, _collect, _urls, is_official


@check("random_domain_entropy", "URL", "S", 20, "Domain name looks machine-generated (high entropy, few vowels)", needs="urls")
def entropy(ctx):
    def f(u):
        label = u["reg"].split(".")[0]
        if len(label) < 9 or is_official(u["host"]) or "-" in label:
            return
        p = [label.count(c) / len(label) for c in set(label)]
        h = -sum(x * math.log2(x) for x in p)
        v = sum(c in "aeiou" for c in label) / len(label)
        if h > 3.3 and (v < 0.22 or v > 0.6 or sum(c.isdigit() for c in label) >= 3):
            return f"'{label}' entropy {h:.1f}, vowel ratio {v:.2f}"
    return _collect(ctx, f)
