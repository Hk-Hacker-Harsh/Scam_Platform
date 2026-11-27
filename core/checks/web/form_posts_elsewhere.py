"""Form submits data to a different domain, a bot API (Telegram/Discord) or plain http"""
import re
from ...engine import check
from ...extract import registered_domain
from .common import _page_host, _soup
from urllib.parse import urlsplit


@check("form_posts_elsewhere", "Website", "H", 35, "Form submits data to a different domain, a bot API (Telegram/Discord) or plain http", needs="html")
def form_posts_elsewhere(ctx):
    s = _soup(ctx)
    host = _page_host(ctx)
    out = []
    for f in s.find_all("form"):
        act = (f.get("action") or "").strip()
        if re.search(r"api\.telegram\.org/bot|discord(app)?\.com/api/webhooks|formspree|script\.google\.com|webhook", act, re.I):
            out.append(f"form posts to {act[:60]}")
        elif act.startswith("http") and host and registered_domain(urlsplit(act).hostname or "") != registered_domain(host):
            out.append(f"form posts to {urlsplit(act).hostname}")
        elif act.startswith("http://"):
            out.append("form posts over plain http")
    if re.search(r"api\.telegram\.org/bot\d+:", ctx.html):
        out.append("Telegram bot token embedded in page code (data exfiltration)")
    return out[:3]
