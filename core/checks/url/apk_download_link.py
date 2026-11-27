"""Link points directly to an .apk file or app-download page"""
from ...engine import check
from .common import _collect, _urls


@check("apk_download_link", "URL", "S", 35, "Link points directly to an .apk file or app-download page", needs="urls")
def apk_link(ctx):
    return _collect(ctx, lambda u: "link to .apk file" if u["path"].lower().endswith((".apk", ".apks", ".xapk")) else None)
