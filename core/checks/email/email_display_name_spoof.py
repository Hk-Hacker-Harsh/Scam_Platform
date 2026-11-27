"""Display name names a brand but the address is from a different domain"""
from ...engine import check
from ..url.common import _brand_in, is_official
from .common import _hdr
from email.utils import parseaddr


@check("email_display_name_spoof", "Email", "H", 40, "Display name names a brand but the address is from a different domain", needs="headers")
def display_spoof(ctx):
    name, addr = parseaddr(_hdr(ctx, "From"))
    dom = addr.split("@")[-1].lower()
    b = _brand_in(name)
    if b and addr and not is_official(dom):
        return f"display name '{name}' ({b}) but address is {addr}"
