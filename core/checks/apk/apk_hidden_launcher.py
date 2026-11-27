"""No launcher icon, or code that hides the icon after install"""
from ...engine import check


@check("apk_hidden_launcher", "APK", "S", 25, "No launcher icon, or code that hides its icon after install (stays hidden on the phone)", needs="apk")
def hidden(ctx):
    a = ctx.apk
    out = []
    if a.get("launcher") is False:
        out.append("no launcher activity in the manifest")
    if "hide_icon" in (a.get("api_refs") or []) and a.get("launcher") is not False:
        out.append("calls setComponentEnabledSetting (used to hide the app icon)")
    return out or None
