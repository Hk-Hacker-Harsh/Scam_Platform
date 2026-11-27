"""Page offers a direct .apk download instead of a Play Store link"""
import re
from ...engine import check


@check("apk_download_on_page", "Website", "H", 35, "Page offers a direct .apk download instead of a Play Store link", needs="html")
def apk_dl(ctx):
    m = re.search(r'(?i)href=["\']([^"\']+\.apk)(?:\?[^"\']*)?["\']', ctx.html)
    return f"direct APK download: {m.group(1)[:70]}" if m else None
