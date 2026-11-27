"""Text obfuscation: zero-width characters, fancy Unicode letters, mixed scripts inside words"""
import re
from ...engine import check
from ...extract import ZW_RE, scripts_in


@check("text_obfuscation", "Message", "S", 25, "Text obfuscation: zero-width characters, fancy Unicode letters, mixed scripts inside words", needs="text")
def obfusc(ctx):
    why = []
    if ZW_RE.search(ctx.text):
        why.append("invisible characters")
    fancy = sum(1 for c in ctx.text if 0x1D400 <= ord(c) <= 0x1D7FF or 0xFF21 <= ord(c) <= 0xFF5A)
    if fancy >= 4:
        why.append(f"{fancy} styled/full-width letters")
    for w in re.findall(r"\w+", ctx.text):
        sc = scripts_in(w)
        if len(sc) > 1 and "LATIN" in sc and len(w) > 2:
            why.append(f"mixed-script word '{w}'")
            break
    if re.search(r"(?i)\b\w*[a-z]\W[a-z]\W[a-z]\W[a-z]\b", ctx.text) and re.search(r"(?i)o\.?t\.?p|k\.?y\.?c", ctx.text):
        why.append("spaced-out keywords")
    return ", ".join(why) or None
