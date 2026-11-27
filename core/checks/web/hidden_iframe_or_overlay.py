"""Hidden or full-page iframe / overlay (clickjacking, credential capture)"""
from ...engine import check
from .common import _soup


@check("hidden_iframe_or_overlay", "Website", "S", 25, "Hidden or full-page iframe / overlay (clickjacking, credential capture)", needs="html")
def hidden_iframe(ctx):
    s = _soup(ctx)
    for f in s.find_all("iframe"):
        st = (f.get("style") or "").replace(" ", "").lower()
        if "display:none" in st or "visibility:hidden" in st or f.get("width") in ("0", "1") or f.get("height") in ("0", "1") or ("position:absolute" in st and "100%" in st):
            return "hidden or invisible iframe present"
