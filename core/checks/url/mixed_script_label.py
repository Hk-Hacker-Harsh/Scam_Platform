"""One domain label mixes writing scripts (Latin + Cyrillic/Greek)"""
from ...engine import check
from ...extract import scripts_in
from .common import _collect, _decode_host, _urls


@check("mixed_script_label", "URL", "H", 40, "One domain label mixes writing scripts (Latin + Cyrillic/Greek)", needs="urls")
def mixed_script_label(ctx):
    def f(u):
        for label in _decode_host(u["host"]).split("."):
            sc = scripts_in(label)
            if len(sc) > 1:
                return f"label '{label}' mixes {', '.join(sorted(sc))}"
    return _collect(ctx, f)
