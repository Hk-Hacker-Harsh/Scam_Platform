"""Loads extra code at run time (DexClassLoader), the way droppers fetch their real payload"""
from ...engine import check


@check("apk_runtime_code_loading", "APK", "S", 20, "Loads extra code at run time (DexClassLoader) or hides a DEX/APK inside its assets", needs="apk")
def code_loading(ctx):
    a = ctx.apk
    out = []
    if "dex_loader" in (a.get("api_refs") or []):
        out.append("uses DexClassLoader / InMemoryDexClassLoader")
    if a.get("hidden_payloads"):
        out.append("code file hidden in assets: " + ", ".join(a["hidden_payloads"][:3]))
    return out or None
