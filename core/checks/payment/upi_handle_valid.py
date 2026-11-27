"""UPI ID uses a handle that is not a registered UPI PSP handle"""
from ...engine import check
from ...data import UPI_HANDLES


@check("upi_handle_valid", "Payment", "S", 25, "UPI ID uses a handle that is not in our list of UPI app handles (list is partial, so a soft signal)", needs="upis")
def upi_handle(ctx):
    bad = [u for u in ctx.ids["upis"] if u.split("@")[1] not in UPI_HANDLES]
    return f"unknown handle in {bad[0]}" if bad else None
