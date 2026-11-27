"""Zero-width or right-to-left override characters hidden in the text/URL"""
from ...engine import check
from ...extract import ZW_RE


@check("invisible_chars_bidi", "URL", "S", 30, "Zero-width or right-to-left override characters hidden in the text/URL", needs="text")
def invisible_chars(ctx):
    n = len(ZW_RE.findall(ctx.text))
    return f"{n} invisible/bidi control character(s)" if n else None
