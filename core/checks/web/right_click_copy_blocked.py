"""Page blocks right-click / copy / dev-tools to hinder inspection"""
import re
from ...engine import check


@check("right_click_copy_blocked", "Website", "S", 10, "Page blocks right-click / copy / dev-tools to hinder inspection", needs="html")
def no_rightclick(ctx):
    return "right-click or text selection disabled" if re.search(r"(?i)oncontextmenu\s*=\s*[\"']return false|event\.keyCode\s*==\s*123|user-select\s*:\s*none", ctx.html) else None
