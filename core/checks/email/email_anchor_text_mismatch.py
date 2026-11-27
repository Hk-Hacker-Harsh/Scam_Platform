"""A link's visible text shows one site but the real href goes to another"""
import re
from ...engine import check
from ...extract import registered_domain


@check("email_anchor_text_mismatch", "Email", "H", 40, "A link's visible text shows one site but the real href goes to another", needs="any")
def anchor_mismatch(ctx):
    body = getattr(ctx, "email_html", "") or ctx.html or ctx.text
    out = []
    for m in re.finditer(r'(?is)<a\s[^>]*href\s*=\s*["\']?(https?://[^"\'\s>]+)[^>]*>(.*?)</a>', body):
        href, txt = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        t = re.search(r"(?i)(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", txt)
        if t:
            from ...extract import parse_url
            hd = parse_url(href)["reg"]
            if registered_domain(t.group(1).lower()) != hd:
                out.append(f"text shows {t.group(1)} but link goes to {hd}")
    return out[:3]
