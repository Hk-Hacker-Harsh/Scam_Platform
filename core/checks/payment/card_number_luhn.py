"""A valid card number (Luhn) appears in the text - never share these"""
from ...engine import check


@check("card_number_luhn", "Payment", "S", 20, "A valid card number (Luhn) appears in the text - never share these", needs="any")
def cards(ctx):
    c = ctx.ids.get("cards")
    return f"{len(c)} valid-looking card number(s) present" if c else None
